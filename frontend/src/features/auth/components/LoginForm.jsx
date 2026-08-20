import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { GoogleSignInButton } from './GoogleSignInButton';

export const LoginForm = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectTarget = searchParams.get('redirect') || '/dashboard';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = () => {
    const newErrors = {};
    if (!email.trim()) {
      newErrors.email = 'Email address is required';
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = 'Please enter a valid email address';
    }
    if (!password) {
      newErrors.password = 'Password is required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');
    if (!validate()) return;

    setIsSubmitting(true);
    const res = await login(email, password);
    setIsSubmitting(false);

    if (res.success) {
      navigate(redirectTarget, { replace: true });
    } else {
      setServerError(res.message);
    }
  };

  return (
    <div className="space-y-5">
      {serverError && (
        <div className="p-3.5 rounded-xl border border-rose-500/30 bg-rose-950/40 text-rose-300 text-xs font-semibold flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">error</span>
          <span>{serverError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
            Email Address
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (errors.email) setErrors((prev) => ({ ...prev, email: null }));
            }}
            placeholder="name@company.com"
            disabled={isSubmitting}
            className={`w-full px-4 py-2.5 rounded-xl bg-slate-950/60 border ${
              errors.email ? 'border-rose-500 text-rose-200' : 'border-slate-800 text-white focus:border-blue-500'
            } placeholder:text-slate-500 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors disabled:opacity-60`}
          />
          {errors.email && <p className="text-xs text-rose-400 mt-1 font-medium">{errors.email}</p>}
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300">
              Password
            </label>
            <Link
              to="/forgot-password"
              className="text-xs text-blue-400 hover:text-blue-300 font-semibold transition-colors"
            >
              Forgot Password?
            </Link>
          </div>
          <input
            type="password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (errors.password) setErrors((prev) => ({ ...prev, password: null }));
            }}
            placeholder="••••••••"
            disabled={isSubmitting}
            className={`w-full px-4 py-2.5 rounded-xl bg-slate-950/60 border ${
              errors.password ? 'border-rose-500 text-rose-200' : 'border-slate-800 text-white focus:border-blue-500'
            } placeholder:text-slate-500 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors disabled:opacity-60`}
          />
          {errors.password && <p className="text-xs text-rose-400 mt-1 font-medium">{errors.password}</p>}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full mt-2 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-lg shadow-blue-500/25 active:scale-[0.99] transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <>
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Signing in...</span>
            </>
          ) : (
            <span>Sign In</span>
          )}
        </button>
      </form>

      <div className="relative flex items-center justify-center my-4">
        <div className="border-t border-slate-800 w-full" />
        <span className="bg-slate-900 px-3 text-[11px] font-bold uppercase tracking-wider text-slate-500 absolute">
          OR
        </span>
      </div>

      <GoogleSignInButton disabled={isSubmitting} />

      <p className="text-center text-xs text-slate-400 mt-6 font-medium">
        Don't have an account?{' '}
        <Link to={`/register${redirectTarget !== '/dashboard' ? `?redirect=${encodeURIComponent(redirectTarget)}` : ''}`} className="text-blue-400 hover:text-blue-300 font-bold underline-offset-2 hover:underline">
          Create Account
        </Link>
      </p>
    </div>
  );
};
