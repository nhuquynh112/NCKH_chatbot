import React, { useState, useEffect, useCallback } from 'react';
import axiosClient from '../api/axiosClient';
import { ChatContext } from './chat-context';

export const ChatProvider = ({ children }) => {
  const [visitorId, setVisitorId] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [sessions, setSessions] = useState([]); // Lịch sử chat
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);

  // Khởi tạo Visitor ID
  useEffect(() => {
    let vid = localStorage.getItem('visitor_id');
    if (!vid) {
      vid = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15);
      localStorage.setItem('visitor_id', vid);
    }
    setVisitorId(vid);

    const savedSession = localStorage.getItem('chat_session_id');
    if (savedSession) {
      setSessionId(savedSession);
    }
  }, []);

  // Fetch lịch sử các đoạn chat khi có visitorId
  const loadSessions = useCallback(async () => {
    if (!visitorId) return;
    try {
      const res = await axiosClient.get(`/chat/sessions?visitor_id=${visitorId}`);
      if (res.success) {
        setSessions(res.data);
      }
    } catch (error) {
      console.error("Failed to load sessions:", error);
    }
  }, [visitorId]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Fetch tin nhắn khi đổi Session
  const loadMessages = useCallback(async (sid) => {
    try {
      const res = await axiosClient.get(`/chat/sessions/${sid}/messages`);
      if (res.success && res.data.items) {
        setMessages(res.data.items);
      }
    } catch (err) {
      console.error('Failed to load history', err);
      if (err.response?.status === 404) {
        localStorage.removeItem('chat_session_id');
        setSessionId(null);
        setMessages([]);
      }
    }
  }, []);

  useEffect(() => {
    if (sessionId) {
      loadMessages(sessionId);
    } else {
      setMessages([]);
    }
  }, [sessionId, loadMessages]);

  const changeSession = (id) => {
    setSessionId(id);
    localStorage.setItem('chat_session_id', id);
  };

  const createNewSession = () => {
    setSessionId(null);
    localStorage.removeItem('chat_session_id');
    setMessages([]);
  };

  const addTempMessage = (msg) => {
    setMessages(prev => [...prev, msg]);
  };

  const value = {
    visitorId,
    sessionId,
    sessions,
    messages,
    isTyping,
    setIsTyping,
    setSessionId,
    setMessages,
    changeSession,
    createNewSession,
    addTempMessage,
    refreshSessions: loadSessions
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
};
