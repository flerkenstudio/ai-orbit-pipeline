import { createClient } from '@supabase/supabase-js';

const supabaseUrl = 'https://detijdndmqumbslxhrdk.supabase.co';
const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRldGlqZG5kbXF1bWJzbHhocmRrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg3MjMyNjMsImV4cCI6MjEwNDI5OTI2M30.5idtzN0_bTA7mftE1-J0H_2-Qfv6B8DPdDv5DGBDtXo';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
