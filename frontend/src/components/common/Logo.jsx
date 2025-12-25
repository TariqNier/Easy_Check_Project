import React from 'react';
import { Link } from 'react-router-dom';
import { Shield } from 'lucide-react';

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2 group">
      <div className="bg-dark p-2 rounded-lg group-hover:bg-main-green transition-colors">
        <Shield className="w-5 h-5 md:w-6 md:h-6 text-lime-yellow" />
      </div>
      <span className="text-lg md:text-xl font-bold text-dark">Easy Check</span>
    </Link>
  );
}

export default Logo;