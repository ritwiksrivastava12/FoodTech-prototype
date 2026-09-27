import { Navigate, Route, Routes, HashRouter } from 'react-router-dom';
import Nav from './components/Nav.jsx';
import { AuthProvider, useAuth } from './store/auth.jsx';
import Welcome from './pages/Welcome.jsx';
import { Login, Signup, Onboarding } from './pages/Auth.jsx';
import Home from './pages/Home.jsx';
import Meals from './pages/Meals.jsx';
import MealDetail from './pages/MealDetail.jsx';
import CookMode from './pages/CookMode.jsx';
import Planner from './pages/Planner.jsx';
import Kitchen from './pages/Kitchen.jsx';
import Shop from './pages/Shop.jsx';
import Nutrition from './pages/Nutrition.jsx';
import AIPage, { Profile } from './pages/AIProfile.jsx';

function Guard({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page"><div className="skel" style={{ height: 300 }} /></div>;
  if (!user) return <Navigate to="/welcome" replace />;
  return children;
}

export default function App() {
  return (
    <HashRouter>
      <AuthProvider>
        <Nav />
        <Routes>
          <Route path="/welcome" element={<Welcome />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/onboarding" element={<Guard><Onboarding /></Guard>} />
          <Route path="/" element={<Guard><Home /></Guard>} />
          <Route path="/meals" element={<Guard><Meals /></Guard>} />
          <Route path="/meals/:id" element={<Guard><MealDetail /></Guard>} />
          <Route path="/cook/:id" element={<Guard><CookMode /></Guard>} />
          <Route path="/planner" element={<Guard><Planner /></Guard>} />
          <Route path="/kitchen" element={<Guard><Kitchen /></Guard>} />
          <Route path="/shop" element={<Guard><Shop /></Guard>} />
          <Route path="/nutrition" element={<Guard><Nutrition /></Guard>} />
          <Route path="/ai" element={<Guard><AIPage /></Guard>} />
          <Route path="/profile" element={<Guard><Profile /></Guard>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </HashRouter>
  );
}
