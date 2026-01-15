import { headers } from 'next/headers';

interface LayoutProps {
  children: React.ReactNode;
}

export default async function Layout({ children }: LayoutProps) {
  const hdrs = await headers();

  return <>{children}</>;
}
