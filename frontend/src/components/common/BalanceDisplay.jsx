
import { Wallet } from 'lucide-react';

function BalanceDisplay({ balance }) {
  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-lg border border-gray-200">
      <Wallet className="w-4 h-4 text-main-green" />
      <span className="text-sm font-semibold text-dark">
        {balance.toFixed(2)} EGP
      </span>
    </div>
  );
}

export default BalanceDisplay;