import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { useReducedMotion } from 'framer-motion';

const Home = () => {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    if (!prefersReducedMotion) {
      // Simulate loading delay
      setTimeout(() => {
        setLoading(false);
      }, 1000);
    } else {
      setLoading(false);
    }
  }, [prefersReducedMotion]);

  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <div className="card-title">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">Welcome to Finance OS</div>
      </div>
      <div className="card-body">
        <p>Explore your financial data and manage your goals.</p>
      </div>
    </div>
  );
};

export default Home;
