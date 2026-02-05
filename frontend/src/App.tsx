import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { ChatProvider } from './contexts/ChatContext';
import { HomePage } from './pages/HomePage';
import { ChatPage } from './pages/ChatPage';
import { MaintenancePlanPage } from './pages/MaintenancePlanPage';

function App() {
  return (
    <ThemeProvider>
      <ChatProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/maintenance-plan" element={<MaintenancePlanPage />} />
          </Routes>
        </BrowserRouter>
      </ChatProvider>
    </ThemeProvider>
  );
}

export default App;
