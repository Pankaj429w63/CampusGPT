'use client';

import React, { useState } from 'react';
import { Sidebar, NavTab } from './sidebar';
import { DashboardView } from './dashboard-view';
import { ChatView, ChatMessage } from './chat-view';
import {
  TimetableView,
  KnowledgeBaseView,
  FacultyView,
  AcademicView,
  SettingsView,
} from './other-views';
import { MenuIcon, SparklesIcon } from './icons';
import { askCampusGPT } from '@/services/api';

export function CampusGPTDashboard() {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-demo',
      sender: 'assistant',
      text: 'Hello! Welcome to CampusGPT. Ask me questions about campus timetables, syllabus details, faculty office hours, attendance criteria, or university regulations.',
      timestamp: 'Just now',
    },
  ]);

  const handleSendMessage = async (textToSend?: string) => {
    const messageText = (textToSend ?? inputQuery).trim();
    if (!messageText) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: messageText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputQuery('');
    setIsLoading(true);

    if (activeTab === 'dashboard') {
      setActiveTab('ask');
    }

    try {
      const response = await askCampusGPT(messageText);

      const aiMessage: ChatMessage = {
        id: `ai-${Date.now()}`,
        sender: 'assistant',
        text: response.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      const errorText =
        err instanceof Error ? err.message : 'An unexpected error occurred';
      const errorMessage: ChatMessage = {
        id: `ai-err-${Date.now()}`,
        sender: 'assistant',
        text: `Unable to get a response from CampusGPT service.\n\nDetail: ${errorText}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-full bg-[#f8fafc] text-slate-800 antialiased overflow-hidden">
      {/* Dark Navy Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        mobileMenuOpen={mobileMenuOpen}
        setMobileMenuOpen={setMobileMenuOpen}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Navbar */}
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-8">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden cursor-pointer"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open sidebar navigation"
            >
              <MenuIcon className="h-5 w-5" />
            </button>
            <div className="text-sm font-medium text-slate-500 hidden sm:block">
              University Portal <span className="mx-2 text-slate-300">/</span>
              <span className="text-slate-800 font-semibold capitalize">{activeTab}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50/80 px-3 py-1 text-xs font-medium text-blue-700">
              <SparklesIcon className="h-3.5 w-3.5 text-blue-600" />
              <span>CampusGPT AI</span>
            </div>
          </div>
        </header>

        {/* Scrollable Workspace */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-8">
          <div className="mx-auto max-w-5xl">
            {activeTab === 'dashboard' && (
              <DashboardView
                inputQuery={inputQuery}
                setInputQuery={setInputQuery}
                isLoading={isLoading}
                onSendMessage={handleSendMessage}
                setActiveTab={setActiveTab}
              />
            )}

            {activeTab === 'ask' && (
              <ChatView
                messages={messages}
                inputQuery={inputQuery}
                setInputQuery={setInputQuery}
                isLoading={isLoading}
                onSendMessage={() => handleSendMessage()}
              />
            )}

            {activeTab === 'timetable' && <TimetableView />}
            {activeTab === 'knowledge' && <KnowledgeBaseView />}
            {activeTab === 'faculty' && <FacultyView />}
            {activeTab === 'academic' && <AcademicView />}
            {activeTab === 'settings' && <SettingsView />}
          </div>
        </main>
      </div>
    </div>
  );
}
