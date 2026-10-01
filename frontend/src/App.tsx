import React from 'react';
import { WorkspacePage } from './pages/WorkspacePage.tsx';
import { UserSettingsProvider } from './contexts/UserSettingsContext.tsx';

export const App: React.FC = () => {
  return (
    <UserSettingsProvider>
      <WorkspacePage />
    </UserSettingsProvider>
  );
};

export default App;
