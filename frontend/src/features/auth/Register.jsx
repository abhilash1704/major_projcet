import { AuthLayout } from './components/AuthLayout';
import { RegisterForm } from './components/RegisterForm';

export const Register = () => {
  return (
    <AuthLayout title="Create Account" subtitle="Get started with continuous live vehicle clustering & A* routing">
      <RegisterForm />
    </AuthLayout>
  );
};
