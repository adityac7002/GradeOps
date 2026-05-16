import { useState } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Login from './pages/Login';
import InstructorDashboard from './dashboard/InstructorDashboard';
import UploadExam from './uploads/UploadExam';
import ReviewDashboard from './review/ReviewDashboard';
import PlagiarismReport from './analytics/PlagiarismReport';
import { Navbar } from './ui';
import './index.css';

function AppInner() {
  const { user, loading } = useAuth();
  const [page, setPage] = useState('dashboard');
  const [selectedExam, setSelectedExam] = useState(null);

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
      <div className="spinner spinner-lg" />
    </div>
  );

  if (!user) return <Login />;

  const renderPage = () => {
    switch (page) {
      case 'dashboard':  return user.role === 'instructor'
        ? <InstructorDashboard setPage={setPage} setSelectedExam={setSelectedExam} />
        : <ReviewDashboard selectedExam={selectedExam} />;
      case 'upload':     return <UploadExam setPage={setPage} />;
      case 'review':     return <ReviewDashboard selectedExam={selectedExam} />;
      case 'plagiarism': return <PlagiarismReport />;
      default:           return <InstructorDashboard setPage={setPage} setSelectedExam={setSelectedExam} />;
    }
  };

  return (
    <>
      <Navbar page={page} setPage={setPage} />
      {renderPage()}
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}
