import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { ChatProvider } from './contexts/ChatContext';
import { HomePage } from './pages/HomePage';
import { ChatPage } from './pages/ChatPage';
import { MaintenancePlanPage } from './pages/MaintenancePlanPage';
import { TroubleshootPage } from './pages/TroubleshootPage';
import { PartsHelperPage } from './pages/PartsHelperPage';

function App() {
  return (
    <ThemeProvider>
      <ChatProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/maintenance-plan" element={<MaintenancePlanPage />} />
            <Route path="/troubleshoot" element={<TroubleshootPage />} />
            <Route path="/parts" element={<PartsHelperPage />} />
          </Routes>
        </BrowserRouter>
      </ChatProvider>
    </ThemeProvider>
  );
}

export default App;
