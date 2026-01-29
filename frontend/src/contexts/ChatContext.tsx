import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import type { Chat, ChatMessage } from '../types';

const STORAGE_KEY = 'home-ops-copilot-chats';

interface ChatContextType {
  chats: Chat[];
  currentChatId: string | null;
  currentChat: Chat | null;
  createChat: () => string;
  deleteChat: (chatId: string) => void;
  selectChat: (chatId: string) => void;
  updateChatTitle: (chatId: string, title: string) => void;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (messageId: string, updates: Partial<ChatMessage>) => void;
  exportChat: (chatId: string) => void;
  clearCurrentChat: () => void;
}

const ChatContext = createContext<ChatContextType | null>(null);

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function generateTitle(messages: ChatMessage[]): string {
  if (messages.length === 0) return 'New Chat';
  const firstQuestion = messages[0].question;
  if (firstQuestion.length <= 40) return firstQuestion;
  return firstQuestion.slice(0, 40) + '...';
}

export function ChatProvider({ children }: { children: ReactNode }) {
  const [chats, setChats] = useState<Chat[]>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as Chat[];
        // Filter out any messages that were loading when saved
        return parsed.map((chat) => ({
          ...chat,
          messages: chat.messages.filter((msg) => !msg.isLoading),
        }));
      } catch {
        return [];
      }
    }
    return [];
  });

  const [currentChatId, setCurrentChatId] = useState<string | null>(() => {
    // Select the most recent chat if any exist
    if (chats.length > 0) {
      const sorted = [...chats].sort((a, b) => b.updatedAt - a.updatedAt);
      return sorted[0].id;
    }
    return null;
  });

  // Save to localStorage whenever chats change
  useEffect(() => {
    const chatsToSave = chats.map((chat) => ({
      ...chat,
      messages: chat.messages.filter((msg) => !msg.isLoading),
    }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chatsToSave));
  }, [chats]);

  const currentChat = chats.find((c) => c.id === currentChatId) ?? null;

  const createChat = useCallback(() => {
    const newChat: Chat = {
      id: generateId(),
      title: 'New Chat',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setChats((prev) => [newChat, ...prev]);
    setCurrentChatId(newChat.id);
    return newChat.id;
  }, []);

  const deleteChat = useCallback((chatId: string) => {
    setChats((prev) => prev.filter((c) => c.id !== chatId));
    setCurrentChatId((prevId) => {
      if (prevId === chatId) {
        // Select another chat or null
        const remaining = chats.filter((c) => c.id !== chatId);
        if (remaining.length > 0) {
          const sorted = [...remaining].sort((a, b) => b.updatedAt - a.updatedAt);
          return sorted[0].id;
        }
        return null;
      }
      return prevId;
    });
  }, [chats]);

  const selectChat = useCallback((chatId: string) => {
    setCurrentChatId(chatId);
  }, []);

  const updateChatTitle = useCallback((chatId: string, title: string) => {
    setChats((prev) =>
      prev.map((chat) =>
        chat.id === chatId ? { ...chat, title, updatedAt: Date.now() } : chat
      )
    );
  }, []);

  const addMessage = useCallback((message: ChatMessage) => {
    if (!currentChatId) return;

    setChats((prev) =>
      prev.map((chat) => {
        if (chat.id !== currentChatId) return chat;

        const newMessages = [...chat.messages, message];
        const shouldUpdateTitle = chat.messages.length === 0 && chat.title === 'New Chat';

        return {
          ...chat,
          messages: newMessages,
          title: shouldUpdateTitle ? generateTitle(newMessages) : chat.title,
          updatedAt: Date.now(),
        };
      })
    );
  }, [currentChatId]);

  const updateMessage = useCallback((messageId: string, updates: Partial<ChatMessage>) => {
    if (!currentChatId) return;

    setChats((prev) =>
      prev.map((chat) => {
        if (chat.id !== currentChatId) return chat;

        return {
          ...chat,
          messages: chat.messages.map((msg) =>
            msg.id === messageId ? { ...msg, ...updates } : msg
          ),
          updatedAt: Date.now(),
        };
      })
    );
  }, [currentChatId]);

  const exportChat = useCallback((chatId: string) => {
    const chat = chats.find((c) => c.id === chatId);
    if (!chat || chat.messages.length === 0) return;

    const markdown = chat.messages
      .filter((msg) => msg.response)
      .map((msg) => {
        const lines: string[] = [];
        lines.push(`## Q: ${msg.question}`);
        lines.push('');
        if (msg.response) {
          lines.push(msg.response.answer);
          lines.push('');
          lines.push(`**Risk Level:** ${msg.response.risk_level}`);
          if (msg.response.citations.length > 0) {
            lines.push('');
            lines.push('### Sources');
            msg.response.citations.forEach((citation, i) => {
              let source = `${i + 1}. ${citation.source}`;
              if (citation.page) source += ` (p. ${citation.page})`;
              if (citation.section) source += ` - ${citation.section}`;
              lines.push(source);
            });
          }
        } else if (msg.error) {
          lines.push(`*Error: ${msg.error}*`);
        }
        lines.push('');
        lines.push('---');
        lines.push('');
        return lines.join('\n');
      })
      .join('\n');

    const header = `# ${chat.title}\n\n*Exported: ${new Date().toLocaleString()}*\n\n---\n\n`;
    const fullMarkdown = header + markdown;

    const blob = new Blob([fullMarkdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-${new Date().toISOString().split('T')[0]}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [chats]);

  const clearCurrentChat = useCallback(() => {
    if (!currentChatId) return;

    setChats((prev) =>
      prev.map((chat) =>
        chat.id === currentChatId
          ? { ...chat, messages: [], title: 'New Chat', updatedAt: Date.now() }
          : chat
      )
    );
  }, [currentChatId]);

  return (
    <ChatContext.Provider
      value={{
        chats,
        currentChatId,
        currentChat,
        createChat,
        deleteChat,
        selectChat,
        updateChatTitle,
        addMessage,
        updateMessage,
        exportChat,
        clearCurrentChat,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}
