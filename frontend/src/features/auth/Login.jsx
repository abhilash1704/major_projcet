import { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { AuthLayout } from './components/AuthLayout';
import { LoginForm } from './components/LoginForm';
import { useAuth } from './AuthContext';

export const Login = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { isAuthenticated, setDirectAuthSession, getCurrentUser } = useAuth();
  
  const token = searchParams.get('token');
  const refreshToken = searchParams.get('refresh_token');
  const redirectTarget = searchParams.get('redirect') || '/dashboard';

  useEffect(() => {
    if (token) {
      setDirectAuthSession({ name: 'Authenticated User' }, token, refreshToken);
      getCurrentUser();
      navigate(redirectTarget, { replace: true });
    } else if (isAuthenticated) {
      navigate(redirectTarget, { replace: true });
    }
  }, [token, refreshToken, redirectTarget, setDirectAuthSession, getCurrentUser, isAuthenticated, navigate]);

  return (
    <AuthLayout title="Sign In to RouteFlow" subtitle="Access your intelligent urban navigation platform">
      <LoginForm />
    </AuthLayout>
  );
};
