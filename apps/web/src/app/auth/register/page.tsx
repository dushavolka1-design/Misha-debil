import { Suspense } from 'react';
import { Skeleton } from '@dar/ui';
import AuthClient from '../../../components/auth/AuthClient';

export default function RegisterPage() {
  return <Suspense fallback={<Skeleton height={200} />}><AuthClient mode="register" /></Suspense>;
}
