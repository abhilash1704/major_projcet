import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { GoogleSignInButton } from './GoogleSignInButton';

export const RegisterForm = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectTarget = searchParams.get('redirect') || '/dashboard';

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = () => {
    const newErrors = {};
    if (!name.trim()) {
      newErrors.name = 'Full Name is required';
    }
    if (!email.trim()) {
      newErrors.email = 'Email address is required';
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = 'Please enter a valid email address';
    }
    if (!password) {
      newErrors.password = 'Password is required';
    } else if (password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters long';
    }
    if (!confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');
    if (!validate()) return;

    setIsSubmitting(true);
    const res = await register({ name, email, password, confirmPassword });
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

      <form onSubmit={handleSubmit} className="space-y-3.5" noValidate>
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1">
            Full Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (errors.name) setErrors((prev) => ({ ...prev, name: null }));
            }}
            placeholder="John Doe"
            disabled={isSubmitting}
            className={`w-full px-4 py-2.5 rounded-xl bg-slate-950/60 border ${
              errors.name ? 'border-rose-500 text-rose-200' : 'border-slate-800 text-white focus:border-blue-500'
            } placeholder:text-slate-500 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors disabled:opacity-60`}
          />
          {errors.name && <p className="text-xs text-rose-400 mt-1 font-medium">{errors.name}</p>}
        </div>

        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1">
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
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1">
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (errors.password) setErrors((prev) => ({ ...prev, password: null }));
            }}
            placeholder="Minimum 6 characters"
            disabled={isSubmitting}
            className={`w-full px-4 py-2.5 rounded-xl bg-slate-950/60 border ${
              errors.password ? 'border-rose-500 text-rose-200' : 'border-slate-800 text-white focus:border-blue-500'
            } placeholder:text-slate-500 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors disabled:opacity-60`}
          />
          {errors.password && <p className="text-xs text-rose-400 mt-1 font-medium">{errors.password}</p>}
        </div>

        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1">
            Confirm Password
          </label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => {
              setConfirmPassword(e.target.value);
              if (errors.confirmPassword) setErrors((prev) => ({ ...prev, confirmPassword: null }));
            }}
            placeholder="Re-enter password"
            disabled={isSubmitting}
            className={`w-full px-4 py-2.5 rounded-xl bg-slate-950/60 border ${
              errors.confirmPassword ? 'border-rose-500 text-rose-200' : 'border-slate-800 text-white focus:border-blue-500'
            } placeholder:text-slate-500 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors disabled:opacity-60`}
          />
          {errors.confirmPassword && (
            <p className="text-xs text-rose-400 mt-1 font-medium">{errors.confirmPassword}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full mt-2 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-lg shadow-blue-500/25 active:scale-[0.99] transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <>
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Creating account...</span>
            </>
          ) : (
            <span>Create Account</span>
          )}
        </button>
      </form>

      <div className="relative flex items-center justify-center my-3">
        <div className="border-t border-slate-800 w-full" />
        <span className="bg-slate-900 px-3 text-[11px] font-bold uppercase tracking-wider text-slate-500 absolute">
          OR
        </span>
      </div>

      <GoogleSignInButton disabled={isSubmitting} />

      <p className="text-center text-xs text-slate-400 mt-5 font-medium">
        Already have an account?{' '}
        <Link to={`/login${redirectTarget !== '/dashboard' ? `?redirect=${encodeURIComponent(redirectTarget)}` : ''}`} className="text-blue-400 hover:text-blue-300 font-bold underline-offset-2 hover:underline">
          Sign In
        </Link>
      </p>
    </div>
  );
};
