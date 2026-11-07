import React from 'react';
import {
  GraduationCapIcon,
  LayoutDashboardIcon,
  MessageSquareIcon,
  CalendarIcon,
  BookOpenIcon,
  UsersIcon,
  FileTextIcon,
  SettingsIcon,
  XIcon,
} from './icons';

export type NavTab = 'dashboard' | 'ask' | 'timetable' | 'knowledge' | 'faculty' | 'academic' | 'settings';

interface SidebarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
}

export function Sidebar({
  activeTab,
  setActiveTab,
  mobileMenuOpen,
  setMobileMenuOpen,
}: SidebarProps) {
  const navItems = [
    { id: 'dashboard' as NavTab, label: 'Dashboard', icon: LayoutDashboardIcon },
    { id: 'ask' as NavTab, label: 'Ask CampusGPT', icon: MessageSquareIcon },
    { id: 'timetable' as NavTab, label: 'Timetable', icon: CalendarIcon },
    { id: 'knowledge' as NavTab, label: 'Knowledge Base', icon: BookOpenIcon },
    { id: 'faculty' as NavTab, label: 'Faculty Info', icon: UsersIcon },
    { id: 'academic' as NavTab, label: 'Academic Info', icon: FileTextIcon },
    { id: 'settings' as NavTab, label: 'Settings', icon: SettingsIcon },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-xs lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Navy Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-[#0f172a] text-slate-200 transition-transform duration-300 ease-in-out lg:static lg:translate-x-0 ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* CampusGPT Brand Header */}
        <div className="flex h-16 items-center justify-between border-b border-slate-800 px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-md shadow-blue-500/25">
              <GraduationCapIcon className="h-6 w-6" />
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
                Campus<span className="text-blue-400">GPT</span>
              </span>
              <p className="text-[11px] font-medium text-slate-400">Smart University Platform</p>
            </div>
          </div>
          <button
            type="button"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white lg:hidden"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Close sidebar navigation"
          >
            <XIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation list */}
        <nav className="flex-1 space-y-1.5 px-3 py-6" aria-label="Main Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setActiveTab(item.id);
                  setMobileMenuOpen(false);
                }}
                className={`group flex w-full items-center gap-3.5 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30 font-semibold'
                    : 'text-slate-400 hover:bg-slate-800/80 hover:text-slate-100'
                }`}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon
                  className={`h-5 w-5 transition-colors ${
                    isActive ? 'text-white' : 'text-slate-400 group-hover:text-slate-200'
                  }`}
                />
                <span>{item.label}</span>
                {isActive && (
                  <span className="ml-auto h-1.5 w-1.5 rounded-full bg-white" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Sidebar Footer status */}
        <div className="border-t border-slate-800/90 p-4">
          <div className="rounded-xl bg-slate-900/80 p-3.5 border border-slate-800">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
              <span className="flex h-2 w-2 rounded-full bg-emerald-500" />
              <span>Campus AI System</span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400">Interactive Preview (v1.0)</p>
          </div>
        </div>
      </aside>
    </>
  );
}

