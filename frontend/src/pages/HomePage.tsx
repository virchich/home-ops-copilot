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
            <div key={mode.id} className="w-full sm:w-80">
              <ModeCardComponent mode={mode} />
            </div>
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
      <div className="relative bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 opacity-60 cursor-not-allowed">
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
      className="group bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 hover:border-blue-500 dark:hover:border-blue-400 hover:shadow-lg transition-all"
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
