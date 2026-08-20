import { useState } from 'react';
import { authService } from '../authService';

export const GoogleSignInButton = ({ disabled }) => {
  const [isConnecting, setIsConnecting] = useState(false);

  const handleClick = () => {
    setIsConnecting(true);
    const googleUrl = authService.getGoogleAuthUrl();
    window.location.href = googleUrl;
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled || isConnecting}
      className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl border border-slate-700 bg-slate-800/80 hover:bg-slate-800 text-slate-200 hover:text-white text-sm font-semibold transition-all active:scale-[0.99] disabled:opacity-60 disabled:cursor-not-allowed shadow-sm"
    >
      {isConnecting ? (
        <span className="inline-flex items-center gap-2 text-slate-300">
          <span className="w-4 h-4 border-2 border-slate-400 border-t-white rounded-full animate-spin" />
          Connecting to Google...
        </span>
      ) : (
        <>
          <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
            <path
              fill="#EA4335"
              d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.2 9 5 12 5z"
            />
            <path
              fill="#4285F4"
              d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"
            />
            <path
              fill="#FBBC05"
              d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12 0 14.8s.7 5.1 1.9 7.5l3.7-2.9c-.2-.7-.4-1.5-.4-2.3z"
            />
            <path
              fill="#34A853"
              d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.2-6.4-5.2L1.9 16.1C3.7 19.8 7.5 23 12 23z"
            />
          </svg>
          <span>Continue with Google</span>
        </>
      )}
    </button>
  );
};
