import { Store } from 'lucide-react';
import ThemeToggle from './ThemeToggle';

export default function Header() {
  return (
    <header className="w-full bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200/50 dark:border-gray-800/50 sticky top-0 z-50 shadow-sm transition-colors duration-300">
      <div className="max-w-6xl mx-auto px-4 md:px-6 py-4 flex justify-between items-center">
        
        {/* Logo Section */}
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-br from-blue-600 to-indigo-600 p-2.5 rounded-xl shadow-md shadow-blue-200 dark:shadow-none">
            <Store className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg md:text-xl font-extrabold text-gray-900 dark:text-white tracking-tight leading-tight">Amazon to Shopify</h1>
            <p className="text-[10px] md:text-xs text-blue-600 dark:text-blue-400 font-bold tracking-wide uppercase">Bridge Dashboard</p>
          </div>
        </div>
        
        {/* Theme Toggle */}
        <div className="flex items-center">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}