import { Link } from 'react-router-dom';
import { ThemeToggle } from '../components/ThemeToggle';

interface ModeCard {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  path: string;
  available: boolean;
}

const modes: ModeCard[] = [
  {
    id: 'chat',
    title: 'Ask a Question',
    description: 'Get answers about your home systems with cited sources and risk assessments.',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
      </svg>
    ),
    path: '/chat',
    available: true,
  },
  {
    id: 'maintenance-plan',
    title: 'Maintenance Plan',
    description: 'Generate seasonal maintenance checklists based on your house profile.',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
    path: '/maintenance-plan',
    available: true,
  },
  {
    id: 'troubleshoot',
    title: 'Troubleshoot',
    description: 'Guided diagnostic for home system issues with safety guardrails.',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
    path: '/troubleshoot',
    available: true,
  },
  {
    id: 'parts',
    title: 'Parts Helper',
    description: 'Find replacement parts, filters, and consumables for your home systems.',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11.42 15.17l-5.1-5.1a2.5 2.5 0 010-3.54l.7-.7a2.5 2.5 0 013.54 0l5.1 5.1m-3.54 3.54l5.1 5.1a2.5 2.5 0 003.54 0l.7-.7a2.5 2.5 0 000-3.54l-5.1-5.1m-3.54 3.54l3.54-3.54" />
      </svg>
    ),
    path: '/parts',
    available: true,
  },
];

export function HomePage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Home Ops Copilot</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Your home maintenance assistant</p>
          </div>
          <ThemeToggle />
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-4xl mx-auto px-4 py-8 sm:py-12">
        <div className="text-center mb-8 sm:mb-12">
          <h2 className="text-2xl sm:text-3xl font-semibold text-gray-900 dark:text-white mb-3">
            What would you like to do?
          </h2>
          <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto">
            Choose a mode below to get started with your home maintenance tasks.
          </p>
        </div>

        {/* Mode cards grid */}
        <div className="flex flex-wrap justify-center gap-4 sm:gap-6">
          {modes.map((mode) => (
            <ModeCardComponent key={mode.id} mode={mode} />
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 py-3">
        <div className="max-w-4xl mx-auto px-4 text-center text-xs text-gray-500 dark:text-gray-400">
          Powered by RAG • All answers include source citations
        </div>
      </footer>
    </div>
  );
}

function ModeCardComponent({ mode }: { mode: ModeCard }) {
  if (!mode.available) {
    return (
      <div className="relative w-full sm:w-80 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 opacity-60 cursor-not-allowed">
        <div className="absolute top-3 right-3 px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 text-xs rounded-full">
          Coming soon
        </div>
        <div className="text-gray-400 dark:text-gray-500 mb-4">{mode.icon}</div>
        <h3 className="text-lg font-medium text-gray-600 dark:text-gray-400 mb-2">{mode.title}</h3>
        <p className="text-sm text-gray-400 dark:text-gray-500">{mode.description}</p>
      </div>
    );
  }

  return (
    <Link
      to={mode.path}
      className="group w-full sm:w-80 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 hover:border-blue-500 dark:hover:border-blue-400 hover:shadow-lg transition-all"
    >
      <div className="text-blue-600 dark:text-blue-400 mb-4 group-hover:scale-110 transition-transform">
        {mode.icon}
      </div>
      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
        {mode.title}
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-400">{mode.description}</p>
      <div className="mt-4 flex items-center text-sm text-blue-600 dark:text-blue-400 font-medium">
        <span>Get started</span>
        <svg className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </Link>
  );
}
