'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Trash2, Key, Copy, Check, Plus, AlertTriangle } from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { MagicCard } from '@/components/ui/magic-card';
import { AnimatedShinyText } from '@/components/ui/animated-shiny-text';
import { Project, APIKey } from '@/lib/api';
import {
  useProject,
  useAPIKeys,
  useUpdateProject,
  useDeleteProject,
  useCreateAPIKey,
  useDeleteAPIKey
} from '@/hooks/use-queries';
import { toast } from 'sonner';

const projectFormSchema = z.object({
  name: z.string().min(1, 'Project name is required').max(100, 'Project name must be less than 100 characters'),
  domain: z.string().max(255, 'Domain must be less than 255 characters').optional().or(z.literal('')),
});

type ProjectFormValues = z.infer<typeof projectFormSchema>;

const apiKeyFormSchema = z.object({
  name: z.string().min(1, 'API key name is required').max(100, 'API key name must be less than 100 characters'),
});

type APIKeyFormValues = z.infer<typeof apiKeyFormSchema>;

export default function ProjectSettingsPage() {
  const router = useRouter();
  const params = useParams();
  const projectSlug = params.id as string; // Directory is [id], but value is slug

  const { data: project, isLoading: projectLoading } = useProject(projectSlug);
  const { data: apiKeys = [], isLoading: keysLoading } = useAPIKeys(projectSlug);
  const { mutate: updateProject, isPending: saving } = useUpdateProject();
  const { mutate: createAPIKey } = useCreateAPIKey();
  const { mutate: deleteAPIKey } = useDeleteAPIKey();
  const { mutate: deleteProject, isPending: deletingProject } = useDeleteProject();

  const [createKeyDialogOpen, setCreateKeyDialogOpen] = useState(false);
  const [newKey, setNewKey] = useState<{ key: string; apiKey: APIKey } | null>(null);
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);

  const projectForm = useForm<ProjectFormValues>({
    resolver: zodResolver(projectFormSchema),
    defaultValues: {
      name: '',
      domain: '',
    },
  });

  const apiKeyForm = useForm<APIKeyFormValues>({
    resolver: zodResolver(apiKeyFormSchema),
    defaultValues: {
      name: '',
    },
  });

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (!storedUser) {
      router.push('/login');
      return;
    }
  }, [router]);

  useEffect(() => {
    if (project) {
      projectForm.reset({
        name: project.name,
        domain: project.domain || '',
      });
    }
  }, [project, projectForm]);

  const loading = projectLoading || keysLoading;

  const onProjectSubmit = (values: ProjectFormValues) => {
    updateProject(
      { slug: projectSlug, name: values.name, domain: values.domain || undefined },
      {
        onSuccess: () => {
          toast.success('Project updated successfully');
        },
        onError: () => {
          toast.error('Failed to update project');
        }
      }
    );
  };

  const onCreateAPIKey = (values: APIKeyFormValues) => {
    if (!project) return;
    createAPIKey(
      { projectId: project.id, name: values.name },
      {
        onSuccess: (result) => {
          setNewKey(result);
          setCreateKeyDialogOpen(false);
          apiKeyForm.reset();
          toast.success('API key created successfully');
        },
        onError: () => {
          toast.error('Failed to create API key');
        }
      }
    );
  };

  const onDeleteAPIKey = (keyId: string) => {
    deleteAPIKey(
      { keyId, projectSlug },
      {
        onSuccess: () => {
          toast.success('API key deleted successfully');
        },
        onError: () => {
          toast.error('Failed to delete API key');
        }
      }
    );
  };

  const onDeleteProject = () => {
    deleteProject(projectSlug, {
      onSuccess: () => {
        toast.success('Project deleted successfully');
        router.push('/dashboard');
      },
      onError: () => {
        toast.error('Failed to delete project');
      }
    });
  };

  const copyToClipboard = async (text: string, keyId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKeyId(keyId);
      toast.success('Copied to clipboard');
      setTimeout(() => setCopiedKeyId(null), 2000);
    } catch (error) {
      toast.error('Failed to copy to clipboard');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-indigo-600"></div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Project not found</CardTitle>
            <CardDescription className="text-base mt-2">
              The project you're looking for doesn't exist.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          <AnimatedShinyText className="!text-gray-900 dark:!text-gray-100">
            Project Settings
          </AnimatedShinyText>
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Manage your project settings, API keys, and more.
        </p>
      </div>

      <Tabs defaultValue="general" className="space-y-4">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="danger">Danger Zone</TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Project Information</CardTitle>
              <CardDescription>
                Update your project name and domain settings.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...projectForm}>
                <form onSubmit={projectForm.handleSubmit(onProjectSubmit)} className="space-y-4">
                  <FormField
                    control={projectForm.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Project Name</FormLabel>
                        <FormControl>
                          <Input placeholder="My Project" {...field} />
                        </FormControl>
                        <FormDescription>
                          A descriptive name for your project.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={projectForm.control}
                    name="domain"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Domain (Optional)</FormLabel>
                        <FormControl>
                          <Input placeholder="example.com" {...field} />
                        </FormControl>
                        <FormDescription>
                          The domain associated with this project for validation.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="flex items-center gap-2 pt-4">
                    <Button type="submit" disabled={saving}>
                      {saving ? 'Saving...' : 'Save Changes'}
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>

          <MagicCard className="p-6">
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Project Details
              </h3>
              <div className="space-y-1">
                <p className="text-sm">
                  <span className="font-medium">Created:</span>{' '}
                  {new Date(project.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </p>
                <p className="text-sm">
                  <span className="font-medium">Project ID:</span>{' '}
                  <code className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                    {project.id}
                  </code>
                </p>
              </div>
            </div>
          </MagicCard>
        </TabsContent>

        <TabsContent value="api-keys" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>API Keys</CardTitle>
                  <CardDescription>
                    Manage API keys for authenticating requests to your project.
                  </CardDescription>
                </div>
                <Button onClick={() => setCreateKeyDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create API Key
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {apiKeys.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <Key className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No API keys yet. Create your first API key to get started.</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Key Prefix</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Last Used</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {apiKeys.map((key) => (
                      <TableRow key={key.id}>
                        <TableCell className="font-medium">{key.name}</TableCell>
                        <TableCell>
                          <code className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                            {key.key_prefix}...
                          </code>
                        </TableCell>
                        <TableCell>
                          <span
                            className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${key.is_active
                              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                              : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
                              }`}
                          >
                            {key.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </TableCell>
                        <TableCell>
                          {key.last_used_at
                            ? new Date(key.last_used_at).toLocaleDateString()
                            : 'Never'}
                        </TableCell>
                        <TableCell>
                          {new Date(key.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell className="text-right">
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button variant="ghost" size="sm">
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Delete API Key</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Are you sure you want to delete the API key "{key.name}"?
                                  This action cannot be undone and any applications using
                                  this key will stop working.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction
                                  onClick={() => onDeleteAPIKey(key.id)}
                                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                >
                                  Delete
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="danger" className="space-y-4">
          <Card className="border-destructive">
            <CardHeader>
              <CardTitle className="text-destructive flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                Danger Zone
              </CardTitle>
              <CardDescription>
                Irreversible and destructive actions.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold mb-2">Delete Project</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                    Once you delete a project, there is no going back. This will
                    permanently delete the project and all associated data including
                    API keys and sessions.
                  </p>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="destructive" disabled={deletingProject}>
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete Project
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This action cannot be undone. This will permanently delete
                          the project "{project.name}" and all of its data including:
                          <ul className="list-disc list-inside mt-2 space-y-1">
                            <li>All API keys</li>
                            <li>All sessions</li>
                            <li>All events and analytics data</li>
                          </ul>
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={onDeleteProject}
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                          {deletingProject ? 'Deleting...' : 'Delete Project'}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Create API Key Dialog */}
      <Dialog open={createKeyDialogOpen} onOpenChange={setCreateKeyDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Create API Key</DialogTitle>
            <DialogDescription>
              Create a new API key for authenticating requests to your project.
            </DialogDescription>
          </DialogHeader>
          <Form {...apiKeyForm}>
            <form
              onSubmit={apiKeyForm.handleSubmit(onCreateAPIKey)}
              className="space-y-4"
            >
              <FormField
                control={apiKeyForm.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>API Key Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Production Key" {...field} />
                    </FormControl>
                    <FormDescription>
                      A descriptive name to identify this API key.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setCreateKeyDialogOpen(false);
                    apiKeyForm.reset();
                  }}
                >
                  Cancel
                </Button>
                <Button type="submit">Create API Key</Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* New API Key Display Dialog */}
      <Dialog
        open={!!newKey}
        onOpenChange={(open) => {
          if (!open) setNewKey(null);
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>API Key Created</DialogTitle>
            <DialogDescription>
              Your API key has been created. Make sure to copy it now as you won't
              be able to see it again.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>API Key</Label>
              <div className="flex items-center gap-2">
                <Input
                  value={newKey?.key || ''}
                  readOnly
                  className="font-mono text-sm"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    newKey && copyToClipboard(newKey.key, newKey.apiKey.id)
                  }
                >
                  {copiedKeyId === newKey?.apiKey.id ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                This is the only time you'll be able to see the full API key.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              onClick={() => {
                setNewKey(null);
                setCreateKeyDialogOpen(false);
              }}
            >
              I've copied the key
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
