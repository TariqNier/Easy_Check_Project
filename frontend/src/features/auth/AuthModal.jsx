import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import toast from 'react-hot-toast';
import { X } from 'lucide-react';
import LoginForm from './LoginForm';
import RegisterForm from './RegisterForm';
import { clearError, loginThunk, registerThunk } from './authSlice';

function AuthModal({ isOpen, onClose }) {
  const dispatch = useDispatch();
  const { loading, error } = useSelector((state) => state.auth);

  const [isLogin, setIsLogin] = useState(true);

  // Clear errors when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      dispatch(clearError());
    }
  }, [isOpen, dispatch]);

  // Handle ESC key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  const handleLoginSubmit = async (data) => {
    try {
      await dispatch(
        loginThunk({
          phone_number: data.phone_number,
          password: data.password,
        })
      ).unwrap();

      toast.success('Login successful! Welcome back! 🎉');
      onClose();
    } catch (error) {
      toast.error(error || 'An error occurred. Please try again.');
    }
  };

  const handleRegisterSubmit = async (data) => {
    try {
      await dispatch(
        registerThunk({
          phone_number: data.phone_number,
          password: data.password,
          confirm_password: data.confirm_password,
        })
      ).unwrap();

      toast.success('Registration successful! Please login. ✅');
      setIsLogin(true);
    } catch (error) {
      toast.error(error || 'An error occurred. Please try again.');
    }
    console.log(data);
    
  };

  const handleToggleMode = () => {
    setIsLogin(!isLogin);
    dispatch(clearError());
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dark/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-md bg-white rounded-4xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex bg-dark p-1 m-4 rounded-2xl">
          <button
            onClick={handleToggleMode}
            type="button"
            disabled={loading}
            className={`flex-1 py-3 rounded-xl font-bold text-sm transition-all ${
              isLogin ? 'bg-lime-yellow text-dark' : 'text-white/60'
            }`}
          >
            Sign In
          </button>
          <button
            onClick={handleToggleMode}
            type="button"
            disabled={loading}
            className={`flex-1 py-3 rounded-xl font-bold text-sm transition-all ${
              !isLogin ? 'bg-lime-yellow text-dark' : 'text-white/60'
            }`}
          >
            Register
          </button>
        </div>

        <button
          onClick={onClose}
          type="button"
          className="absolute top-6 right-6 text-dark/40 hover:text-dark transition-colors z-10"
        >
          <X size={24} />
        </button>

        <div className="p-8 pt-4">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-black text-dark uppercase tracking-tighter">
              {isLogin ? 'Welcome Back' : 'Create Account'}
            </h2>
            <p className="text-sm text-gray-500 mt-2">
              {isLogin ? 'Sign in to continue' : 'Sign up to get started'}
            </p>
          </div>

          {isLogin ? (
            <LoginForm
              onSubmit={handleLoginSubmit}
              loading={loading}
              error={error}
            />
          ) : (
            <RegisterForm
              onSubmit={handleRegisterSubmit}
              loading={loading}
              error={error}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default AuthModal;