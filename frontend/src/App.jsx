import { useState } from 'react';
import Login from './pages/Login';
import InstructorDashboard from './dashboard/InstructorDashboard';
import ReviewDashboard from './review/ReviewDashboard';
import ExamUpload from './uploads/ExamUpload';
import AnalyticsDashboard from './analytics/AnalyticsDashboard';
import Navbar from './ui/Navbar';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ToastProvider } from './hooks/useToast';

function AppContent() {
  const { user, loading } = useAuth();
  const [page, setPage] = useState('dashboard'); // dashboard | review | upload | analytics
  const [selectedExam, setSelectedExam] = useState(null);

  if (loading) return null;
  if (!user) return <Login />;

  const renderPage = () => {
    switch (page) {
      case 'dashboard':
        return <InstructorDashboard setPage={setPage} setSelectedExam={setSelectedExam} />;
      case 'upload':
        return <ExamUpload onComplete={() => setPage('dashboard')} />;
      case 'review':
        return <ReviewDashboard exam={selectedExam} onBack={() => setPage('dashboard')} />;
      case 'analytics':
        return <AnalyticsDashboard exam={selectedExam} onBack={() => setPage('dashboard')} />;
      default:
        return <InstructorDashboard setPage={setPage} setSelectedExam={setSelectedExam} />;
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      <Navbar setPage={setPage} activePage={page} />
      <main className="pt-20">
        {renderPage()}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppContent />
      </ToastProvider>
    </AuthProvider>
  );
}
