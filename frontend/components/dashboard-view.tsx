import React from 'react';
import {
  SparklesIcon,
  SendIcon,
  HelpCircleIcon,
  CalendarIcon,
  BookOpenIcon,
  UsersIcon,
  FileTextIcon,
  ChevronRightIcon,
  MessageSquareIcon,
} from './icons';
import { NavTab } from './sidebar';

interface DashboardViewProps {
  inputQuery: string;
  setInputQuery: (query: string) => void;
  isLoading: boolean;
  onSendMessage: (query?: string) => void;
  setActiveTab: (tab: NavTab) => void;
}

export function DashboardView({
  inputQuery,
  setInputQuery,
  isLoading,
  onSendMessage,
  setActiveTab,
}: DashboardViewProps) {
  const suggestedQuestions = [
    'What is my timetable today?',
    'Explain the attendance requirements.',
    'Show me the academic calendar.',
    'What subjects are covered this semester?',
  ];

  const quickAccessCards = [
    {
      title: 'Timetable',
      description: 'View daily schedule, lectures, rooms and lab timings.',
      tab: 'timetable' as NavTab,
      icon: CalendarIcon,
      colorClass: 'bg-blue-50 text-blue-600 group-hover:bg-blue-600',
    },
    {
      title: 'Knowledge Base',
      description: 'Access official curriculum guidelines, syllabi, and FAQs.',
      tab: 'knowledge' as NavTab,
      icon: BookOpenIcon,
      colorClass: 'bg-indigo-50 text-indigo-600 group-hover:bg-indigo-600',
    },
    {
      title: 'Faculty Information',
      description: 'Department directories, office hours, and faculty profiles.',
      tab: 'faculty' as NavTab,
      icon: UsersIcon,
      colorClass: 'bg-emerald-50 text-emerald-600 group-hover:bg-emerald-600',
    },
    {
      title: 'Academic Information',
      description: 'Examination policies, credit schemes, and grading rules.',
      tab: 'academic' as NavTab,
      icon: FileTextIcon,
      colorClass: 'bg-amber-50 text-amber-600 group-hover:bg-amber-600',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-8 shadow-xs">
        <div className="inline-flex items-center gap-2 rounded-lg bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 mb-3">
          <SparklesIcon className="h-3.5 w-3.5" />
          <span>Next-Gen Academic Intelligence</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          Your Campus, Smarter.
        </h1>
        <p className="mt-2.5 max-w-2xl text-base text-slate-600 leading-relaxed">
          CampusGPT helps students and faculty instantly access university information,
          schedules, academic regulations, syllabus topics, and course resources through
          conversational AI.
        </p>

        {/* AI Question Input */}
        <div className="mt-8">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              onSendMessage();
            }}
            className="relative flex items-center"
          >
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask CampusGPT anything about courses, exams, schedules..."
              className="w-full rounded-xl border border-slate-300 bg-slate-50/70 py-4 pl-4 pr-32 text-sm text-slate-800 shadow-inner placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-hidden focus:ring-4 focus:ring-blue-500/10 transition-all"
            />
            <button
              type="submit"
              disabled={!inputQuery.trim() || isLoading}
              className="absolute right-2.5 flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
            >
              <span>Ask</span>
              <SendIcon className="h-3.5 w-3.5" />
            </button>
          </form>

          {/* Suggested Questions */}
          <div className="mt-4">
            <p className="text-xs font-medium text-slate-500 mb-2.5">
              Suggested questions:
            </p>
            <div className="flex flex-wrap gap-2">
              {suggestedQuestions.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => onSendMessage(question)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 transition-colors cursor-pointer"
                >
                  <HelpCircleIcon className="h-3.5 w-3.5 text-blue-500" />
                  <span>{question}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Quick-Access Cards */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-900">Quick Access</h2>
          <button
            type="button"
            onClick={() => setActiveTab('ask')}
            className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1 cursor-pointer"
          >
            <span>Ask CampusGPT Assistant</span>
            <ChevronRightIcon className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {quickAccessCards.map((card) => {
            const Icon = card.icon;
            return (
              <div
                key={card.title}
                onClick={() => setActiveTab(card.tab)}
                className="group cursor-pointer rounded-xl border border-slate-200/90 bg-white p-5 shadow-xs transition-all hover:border-blue-300 hover:shadow-md"
              >
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-lg group-hover:text-white transition-colors ${card.colorClass}`}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="mt-4 font-semibold text-slate-900 group-hover:text-blue-600 flex items-center justify-between">
                  <span>{card.title}</span>
                  <ChevronRightIcon className="h-4 w-4 text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                </h3>
                <p className="mt-1 text-xs text-slate-500">{card.description}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* AI Assistant Banner */}
      <div className="rounded-xl border border-blue-100 bg-gradient-to-r from-blue-50 to-indigo-50/40 p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs">
            <MessageSquareIcon className="h-5 w-5" />
          </div>
          <div>
            <h4 className="font-semibold text-slate-900 text-sm">Need deep answers from official docs?</h4>
            <p className="text-xs text-slate-600">The CampusGPT conversational assistant queries syllabus guidelines and university policies.</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setActiveTab('ask')}
          className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700 transition-colors shrink-0 cursor-pointer"
        >
          Open Assistant
        </button>
      </div>
    </div>
  );
}

