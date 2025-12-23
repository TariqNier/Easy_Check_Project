import React from 'react';
import { Link } from 'react-router-dom';
import { Search, CreditCard, Wallet, LogOut, X } from 'lucide-react';
import Logo from './Logo';

function MobileMenu({ isOpen, onClose, isAuthenticated, user, onLogout, onLoginClick }) {
  if (!isOpen) return null;

  return (
    <div className="md:hidden fixed w-full z-50 bg-white">
      {/* Mobile Header */}
      <div className="flex justify-between items-center px-4 sm:px-6 md:px-[8vw] py-3 border-b border-gray-200">
        <Logo />
        <button
          onClick={onClose}
          className="p-2 text-dark hover:bg-gray-100 rounded-lg transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Mobile Menu Content */}
      <div className="px-4 py-6 space-y-4 overflow-y-auto bg-white shadow-md">
        {/* Mobile: Guest View */}
        {!isAuthenticated && (
          <button 
            onClick={() => {
              onClose();
              onLoginClick(); // 🆕 Open AuthModal
            }}
            className="w-full px-4 py-3 text-sm font-bold bg-lime-yellow text-dark rounded-lg hover:bg-[#d4ea23] transition-all shadow-md"
          >
            Login
          </button>
        )}

        {/* Mobile: User View */}
        {isAuthenticated && (
          <>
            {/* Balance Card */}
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-12 h-12 bg-main-green rounded-full flex items-center justify-center">
                  <Wallet className="w-6 h-6 text-lime-yellow" />
                </div>
                <div>
                  <p className="text-xs text-gray-500 font-medium">Your Balance</p>
                  <p className="text-lg font-bold text-dark">{user.balance.toFixed(2)} EGP</p>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Link
                to="/search-history"
                className="flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors border border-gray-200"
                onClick={onClose}
              >
                <Search  className="w-5 h-5 text-main-green" />
                <span>Search History</span>
              </Link>

              <Link
                to="/payment-history"
                className="flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors border border-gray-200"
                onClick={onClose}
              >
                <CreditCard className="w-5 h-5 text-main-green" />
                <span>Payment History</span>
              </Link>

              <Link
                to="/add-credit"
                className="flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors border border-gray-200"
                onClick={onClose}
              >
                <Wallet className="w-5 h-5 text-main-green" />
                <span>Add Credit</span>
              </Link>

              <button
                onClick={onLogout}
                className="flex items-center gap-3 w-full px-4 py-3 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-red-200"
              >
                <LogOut className="w-5 h-5" />
                <span>Logout</span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default MobileMenu;