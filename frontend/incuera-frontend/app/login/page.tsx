'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { AnimatedShinyText } from '@/components/ui/animated-shiny-text';
import { DotPattern } from '@/components/ui/dot-pattern';
import { MagicCard } from '@/components/ui/magic-card';
import { Alert, AlertDescription } from '@/components/ui/alert';

export default function LoginPage() {
  const router = useRouter();
  const { theme } = useTheme();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // For now, we'll use a simple approach
      // In production, implement proper authentication
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        setError('Invalid email or password');
        setLoading(false);
        return;
      }

      const data = await response.json();
      
      // Store user in localStorage (simple approach)
      localStorage.setItem('user', JSON.stringify(data.user));
      localStorage.setItem('userId', data.user.id);
      
      router.push('/dashboard');
    } catch (err) {
      setError('Login failed. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-gray-50 px-4 overflow-hidden">
      {/* Background Pattern */}
      <DotPattern
        className="opacity-20"
        width={20}
        height={20}
        cx={1}
        cy={1}
        cr={1}
      />
      
      <div className="relative z-10 w-full max-w-md">
        <Card className="w-full max-w-md border-none p-0 shadow-none">
          <MagicCard
            gradientColor={theme === "dark" ? "#262626" : "#D9D9D955"}
            className="p-0"
          >
            <CardHeader className="border-border border-b p-4 [.border-b]:pb-4">
              <CardTitle className="text-center text-3xl">
                <AnimatedShinyText className="!text-gray-900 dark:!text-gray-100">
                  Incuera Dashboard
                </AnimatedShinyText>
              </CardTitle>
              <CardDescription className="text-center">
                Sign in to manage your projects
              </CardDescription>
            </CardHeader>
            <CardContent className="p-4">
              <form id="login-form" onSubmit={handleSubmit}>
                {error && (
                  <Alert variant="destructive" className="mb-4">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                <div className="grid gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="email">Email address</Label>
                    <Input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@example.com"
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      name="password"
                      type="password"
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>
                </div>
              </form>
            </CardContent>
            <CardFooter className="border-border border-t p-4 [.border-t]:pt-4">
              <Button
                type="submit"
                form="login-form"
                disabled={loading}
                className="w-full"
              >
                {loading ? 'Signing in...' : 'Sign in'}
              </Button>
            </CardFooter>
          </MagicCard>
        </Card>
      </div>
    </div>
  );
}
