import express from 'express';
import http from 'http';
import fs from 'fs';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import { createServer as createViteServer } from 'vite';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = 3000;
const PYTHON_PORT = 8001;
const PYTHON_HOST = '127.0.0.1';

let pythonProcess: ChildProcess | null = null;
let isPythonReady = false;

function resolvePythonExecutable(): string {
  const venvPython = path.resolve(__dirname, '.venv/bin/python');
  if (fs.existsSync(venvPython)) {
    return venvPython;
  }
  const systemPython = '/usr/bin/python3';
  if (fs.existsSync(systemPython)) {
    return systemPython;
  }
  return 'python3';
}

// ---------------------------------------------------------------------------
// Python Backend Supervisor
// ---------------------------------------------------------------------------

function checkPythonHealth(): Promise<boolean> {
  return new Promise((resolve) => {
    const req = http.get(
      {
        hostname: PYTHON_HOST,
        port: PYTHON_PORT,
        path: '/api/health',
        timeout: 1000,
      },
      (res) => {
        resolve(res.statusCode === 200);
      }
    );
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForPython(timeoutMs = 15000): Promise<boolean> {
  const startTime = Date.now();
  while (Date.now() - startTime < timeoutMs) {
    const ready = await checkPythonHealth();
    if (ready) {
      isPythonReady = true;
      console.log(`[FormatAI] Python backend verified healthy on port ${PYTHON_PORT}`);
      return true;
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  console.warn(`[FormatAI] Python backend health check timed out after ${timeoutMs}ms`);
  return false;
}

function startPythonBackend() {
  if (pythonProcess && !pythonProcess.killed) {
    return;
  }

  const pythonBin = resolvePythonExecutable();
  console.log(`[FormatAI] Spawning Python FastAPI backend using ${pythonBin} on port ${PYTHON_PORT}...`);
  pythonProcess = spawn(
    pythonBin,
    ['-m', 'uvicorn', 'backend.main:app', '--host', '0.0.0.0', '--port', String(PYTHON_PORT)],
    {
      cwd: __dirname,
      stdio: ['ignore', 'inherit', 'inherit'],
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
      },
    }
  );

  pythonProcess.on('error', (err) => {
    console.error('[FormatAI] Failed to spawn Python backend process:', err);
    isPythonReady = false;
  });

  pythonProcess.on('exit', (code, signal) => {
    console.warn(`[FormatAI] Python backend exited with code ${code}, signal ${signal}`);
    isPythonReady = false;
    pythonProcess = null;

    // Auto-restart python if exited unexpectedly
    if (signal !== 'SIGTERM' && signal !== 'SIGINT') {
      console.log('[FormatAI] Restarting Python backend in 2 seconds...');
      setTimeout(startPythonBackend, 2000);
    }
  });

  waitForPython().catch(console.error);
}

function cleanupProcesses() {
  if (pythonProcess) {
    console.log('[FormatAI] Stopping Python backend process...');
    pythonProcess.kill('SIGTERM');
    pythonProcess = null;
  }
}

process.on('SIGINT', () => {
  cleanupProcesses();
  process.exit(0);
});

process.on('SIGTERM', () => {
  cleanupProcesses();
  process.exit(0);
});

process.on('exit', () => {
  cleanupProcesses();
});

// ---------------------------------------------------------------------------
// Express Server with API Proxy & Vite Dev Middlewares
// ---------------------------------------------------------------------------

async function createServer() {
  startPythonBackend();

  const app = express();

  // Dedicated Health Check Endpoint with Auto-Wait & Self-Healing
  app.get('/api/health', async (_req, res) => {
    // Ensure Python supervisor is running
    if (!pythonProcess || pythonProcess.killed) {
      startPythonBackend();
    }

    let ready = isPythonReady && (await checkPythonHealth());
    if (!ready) {
      ready = await waitForPython(4000);
    }

    if (ready) {
      return res.status(200).json({
        status: 'ok',
        service: 'FormatAI',
        backend: 'python',
      });
    }

    return res.status(503).json({
      status: 'starting',
      service: 'FormatAI',
      backend: 'python',
      message: 'Python FastAPI backend is initializing, please retry shortly.',
    });
  });

  // API Proxy Handler for all other /api/* routes
  app.use('/api', async (req, res) => {
    // Ensure Python process is active
    if (!pythonProcess || pythonProcess.killed) {
      startPythonBackend();
    }

    // If python is still booting, wait up to 5 seconds
    if (!isPythonReady) {
      await waitForPython(5000);
    }

    const options: http.RequestOptions = {
      hostname: PYTHON_HOST,
      port: PYTHON_PORT,
      path: req.originalUrl,
      method: req.method,
      headers: {
        ...req.headers,
        host: `${PYTHON_HOST}:${PYTHON_PORT}`,
      },
    };

    const proxyReq = http.request(options, (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 500, proxyRes.headers);
      proxyRes.pipe(res);
    });

    proxyReq.on('error', (err) => {
      console.warn(`[FormatAI] Proxy notice for ${req.method} ${req.originalUrl}:`, err.message);
      if (!res.headersSent) {
        res.status(502).json({
          error: 'Backend Python service temporarily unavailable',
          message: err.message,
          hint: 'The Python FastAPI backend is currently initializing. Please retry in a moment.',
        });
      }
    });

    req.pipe(proxyReq);
  });

  // Mount Vite middlewares in development
  const isProd = process.env.NODE_ENV === 'production';
  if (!isProd) {
    const vite = await createViteServer({
      server: {
        middlewareMode: true,
        hmr: false,
      },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.resolve(__dirname, 'dist')));
    app.get('*', (_req, res) => {
      res.sendFile(path.resolve(__dirname, 'dist/index.html'));
    });
  }

  const server = app.listen(PORT, '0.0.0.0', () => {
    console.log(`[FormatAI] Server listening on http://0.0.0.0:${PORT}`);
  });

  return server;
}

createServer().catch((err) => {
  console.error('[FormatAI] Fatal error starting server:', err);
  process.exit(1);
});
