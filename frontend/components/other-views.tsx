import React from 'react';
import { ClockIcon, BookOpenIcon, UsersIcon, FileTextIcon, SettingsIcon } from './icons';

export function TimetableView() {
  const schedule = [
    { time: '09:00 AM - 10:30 AM', subject: 'Data Structures & Algorithms', hall: 'Room 302, Engineering Block', professor: 'Dr. Sharma' },
    { time: '10:45 AM - 12:15 PM', subject: 'Database Management Systems', hall: 'Computer Lab 3', professor: 'Prof. Mehta' },
    { time: '01:30 PM - 03:00 PM', subject: 'Artificial Intelligence & Neural Nets', hall: 'Auditorium Hall B', professor: 'Dr. Rao' },
    { time: '03:15 PM - 04:45 PM', subject: 'Computer Networks Workshop', hall: 'Networking Lab', professor: 'Prof. Verma' },
  ];

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-8 shadow-xs space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Academic Timetable</h2>
        <p className="mt-1 text-sm text-slate-500">
          Live schedule overview across university departments and lecture halls.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {schedule.map((item, idx) => (
          <div key={idx} className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-600 mb-2">
              <ClockIcon className="h-3.5 w-3.5" />
              <span>{item.time}</span>
            </div>
            <h4 className="font-semibold text-slate-900 text-sm">{item.subject}</h4>
            <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
              <span>{item.hall}</span>
              <span className="font-medium text-slate-700">{item.professor}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-dashed border-slate-300 p-4 text-center">
        <p className="text-xs text-slate-500">
          Tip: You can query CampusGPT directly in the chat tab with &quot;What is my timetable today?&quot;
        </p>
      </div>
    </div>
  );
}

export function KnowledgeBaseView() {
  const documents = [
    { title: 'Academic Regulations & Attendance Policy (75% Minimum)', category: 'General University Policy' },
    { title: 'B.Tech Computer Science Syllabus & Course Modules (2025-2026)', category: 'Curriculum & Courses' },
    { title: 'Mid-Semester & End-Semester Grading Scheme', category: 'Evaluations' },
    { title: 'Campus Facility Directory & Laboratory Safety Handbook', category: 'Campus Resources' },
    { title: 'Elective Course Selection & Credit Transfer Procedures', category: 'Academic Affairs' },
    { title: 'Student Research Grants & Innovation Cell Guidelines', category: 'Research & Projects' },
  ];

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-8 shadow-xs space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">University Knowledge Base</h2>
        <p className="mt-1 text-sm text-slate-500">
          Indexed curriculum catalogs, institutional documents, and examination guidelines.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {documents.map((doc, idx) => (
          <div key={idx} className="rounded-xl border border-slate-200 p-4 hover:border-blue-200 hover:bg-blue-50/30 transition-colors">
            <div className="flex items-center gap-2">
              <BookOpenIcon className="h-4 w-4 text-blue-600 shrink-0" />
              <span className="text-[11px] font-semibold text-blue-600 uppercase tracking-wider">{doc.category}</span>
            </div>
            <h4 className="font-semibold text-slate-900 text-sm mt-2">{doc.title}</h4>
          </div>
        ))}
      </div>
    </div>
  );
}

export function FacultyView() {
  const facultyList = [
    { name: 'Dr. Rajesh Sharma', role: 'Head of Department', dept: 'Computer Science & AI', office: 'Room 401, Tech Building' },
    { name: 'Dr. Sunita Rao', role: 'Associate Professor', dept: 'Machine Learning & Data Science', office: 'Room 405, Tech Building' },
    { name: 'Prof. Amit Mehta', role: 'Assistant Professor', dept: 'Systems & Databases', office: 'Room 312, Tech Building' },
    { name: 'Prof. Neha Verma', role: 'Assistant Professor', dept: 'Networks & Security', office: 'Room 314, Tech Building' },
  ];

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-8 shadow-xs space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Faculty Directory</h2>
        <p className="mt-1 text-sm text-slate-500">
          Department heads, course professors, office locations, and consultation hours.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {facultyList.map((faculty, idx) => (
          <div key={idx} className="rounded-xl border border-slate-200 p-4 bg-slate-50/60">
            <div className="flex items-center gap-2">
              <UsersIcon className="h-4 w-4 text-emerald-600 shrink-0" />
              <span className="text-xs font-semibold text-emerald-700">{faculty.role}</span>
            </div>
            <h4 className="font-semibold text-slate-900 text-sm mt-1">{faculty.name}</h4>
            <p className="text-xs text-slate-600 mt-1">{faculty.dept}</p>
            <p className="text-[11px] text-slate-400 mt-2">{faculty.office}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function AcademicView() {
  const policies = [
    { title: '75% Minimum Attendance Requirement', detail: 'Mandatory minimum attendance required to appear in end-semester final examinations.' },
    { title: 'Continuous Internal Evaluation (CIE)', detail: 'Comprises quizzes, lab practicals, assignments, and mid-term assessments totaling 40% weightage.' },
    { title: 'Semester End Examination (SEE)', detail: 'Comprehensive written evaluation covering the full course curriculum totaling 60% weightage.' },
    { title: 'Grade Point System & Transcripts', detail: '10-point relative grading scale computed at the end of each academic semester.' },
  ];

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-8 shadow-xs space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Academic Regulations & Information</h2>
        <p className="mt-1 text-sm text-slate-500">
          Essential university policies, grading criteria, and examination guidelines.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {policies.map((policy, idx) => (
          <div key={idx} className="rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2">
              <FileTextIcon className="h-4 w-4 text-amber-600 shrink-0" />
              <h4 className="font-semibold text-slate-900 text-sm">{policy.title}</h4>
            </div>
            <p className="text-xs text-slate-600 mt-2 leading-relaxed">{policy.detail}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SettingsView() {
  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-8 shadow-xs space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">CampusGPT Preferences</h2>
        <p className="mt-1 text-sm text-slate-500">
          Configuration and university system connection status.
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between rounded-xl border border-slate-200 p-4">
          <div className="flex items-center gap-3">
            <SettingsIcon className="h-5 w-5 text-slate-400" />
            <div>
              <h4 className="font-semibold text-slate-900 text-sm">LLM & RAG Integration</h4>
              <p className="text-xs text-slate-500">Direct university API and knowledge vector retrieval.</p>
            </div>
          </div>
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">Next Phase</span>
        </div>

        <div className="flex items-center justify-between rounded-xl border border-slate-200 p-4">
          <div className="flex items-center gap-3">
            <SettingsIcon className="h-5 w-5 text-slate-400" />
            <div>
              <h4 className="font-semibold text-slate-900 text-sm">Campus Notification Alerts</h4>
              <p className="text-xs text-slate-500">Schedule changes, room reallocation, and deadline reminders.</p>
            </div>
          </div>
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">Active</span>
        </div>
      </div>
    </div>
  );
}

