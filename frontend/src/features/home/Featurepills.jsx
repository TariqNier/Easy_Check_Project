import { Lock, Cloud, ShieldCheck } from 'lucide-react';

const features = [
  {
    id: 1,
    icon: 'check', // غيرنا الـ dot لشكل احترافي أكتر
    label: 'Global Blacklist',
  },
  {
    id: 2,
    icon: 'lock',
    label: 'Carrier Lock',
  },
  {
    id: 3,
    icon: 'icloud',
    label: 'iCloud Status',
  },
];

function FeaturePills() {
  const renderIcon = (iconType) => {
    switch (iconType) {
      case 'check':
        return <ShieldCheck className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-main-green" />;
      case 'lock':
        return <Lock className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-main-green" />;
      case 'icloud':
        return <Cloud className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[#007AFF]" />; // لون أبل الأزرق
      default:
        return <div className="w-2 h-2 bg-main-green rounded-full" />;
    }
  };

  return (
    <div className="flex flex-wrap justify-center gap-3 sm:gap-4 mt-10 px-4">
      {features.map((feature) => (
        <div
          key={feature.id}
          className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-white/80 backdrop-blur-sm border border-gray-100 rounded-full shadow-sm hover:shadow-md hover:border-main-green/30 transition-all cursor-default"
        >
          {renderIcon(feature.icon)}
          <span className="text-xs sm:text-sm font-semibold text-dark/80">
            {feature.label}
          </span>
        </div>
      ))}
    </div>
  );
}

export default FeaturePills;