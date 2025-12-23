import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Toaster } from 'react-hot-toast';
import { verifyAuthThunk } from './features/auth/authSlice';
import AppRouter from './router/AppRouter';
import './App.css';

function App() {
  // const dispatch = useDispatch();
  // const {loading} = useSelector((state) => state.auth);

  // useEffect(() => {
  //   dispatch(verifyAuthThunk());
  // }, [dispatch]);

  // if (loading) {
  //   return (
  //     <div className="flex items-center justify-center min-h-screen bg-white">
  //       <div className="text-center">
  //         <div className="w-16 h-16 border-4 border-main-green border-t-lime-yellow rounded-full animate-spin mx-auto mb-4"></div>
  //         <p className="text-dark font-bold text-lg">Loading...</p>
  //       </div>
  //     </div>
  //   );
  // }

  return (
    <>
      {/* Toast Notifications */}
      <Toaster
        position="top-right"
        reverseOrder={false}
        toastOptions={{
          duration: 1000,
          style: {
            background: '#fff',
            color: '#181818',
            fontWeight: '600',
            fontSize: '14px',
            padding: '16px',
            borderRadius: '12px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
          },
          success: {
            iconTheme: {
              primary: '#073e1d',
              secondary: '#e5fb34',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
      
      <AppRouter />
    </>
  );
}

export default App;