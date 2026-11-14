import { Store, Settings as SettingsIcon, LayoutDashboard } from 'lucide-react';
import ThemeToggle from './ThemeToggle';

export default function Header({ activeTab, setActiveTab }) {
  return (
    <header className="w-full bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200/50 dark:border-gray-800/50 sticky top-0 z-50 shadow-sm transition-colors duration-300">
      <div className="max-w-5xl mx-auto px-4 md:px-6 py-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        
        {/* Logo Section */}
        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="bg-gradient-to-br from-blue-600 to-indigo-600 p-2.5 rounded-xl shadow-md shadow-blue-200 dark:shadow-none">
            <Store className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg md:text-xl font-extrabold text-gray-900 dark:text-white tracking-tight leading-tight">Amazon to Shopify</h1>
            <p className="text-[10px] md:text-xs text-blue-600 dark:text-blue-400 font-bold tracking-wide uppercase">Bridge Dashboard</p>
          </div>
        </div>
        
        {/* Nav & Theme Toggle */}
        <div className="flex flex-wrap items-center justify-between w-full md:w-auto gap-2 md:gap-4">
          <nav className="flex bg-gray-100/50 dark:bg-gray-800/50 p-1 rounded-xl border border-gray-200/50 dark:border-gray-700/50 flex-1 md:flex-none">
            <button 
              onClick={() => setActiveTab('dashboard')}
              className={`flex-1 md:flex-none flex items-center justify-center gap-2 px-3 md:px-5 py-2 text-xs md:text-sm font-semibold rounded-lg transition-all ${activeTab === 'dashboard' ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'}`}
            >
              <LayoutDashboard className="w-4 h-4" /> Dashboard
            </button>
            <button 
              onClick={() => setActiveTab('settings')}
              className={`flex-1 md:flex-none flex items-center justify-center gap-2 px-3 md:px-5 py-2 text-xs md:text-sm font-semibold rounded-lg transition-all ${activeTab === 'settings' ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'}`}
            >
              <SettingsIcon className="w-4 h-4" /> Settings
            </button>
          </nav>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}