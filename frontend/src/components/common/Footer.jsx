import React from 'react';



const brands = [
  { id: 1, emoji: '🍎', name: 'Apple' },
  { id: 2, emoji: '📱', name: 'Samsung' },
  { id: 3, emoji: '📲', name: 'Xiaomi' },
];

function Footer() {
  return (
    <footer className="border-t border-gray-200 py-4 sm:py-6 px-4 bg-white">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-wrap justify-center items-center gap-3 sm:gap-8 text-xs sm:text-sm text-gray-400">
          {/* Copyright */}
          <span className="font-medium">© 2025 IMEI Check Inc.</span>
            

          <span className="hidden sm:inline flex-1"></span>
          
          {/* Brands */}
          <div className="flex items-center gap-3 sm:gap-6">
            {brands.map((brand) => (
              <span key={brand.id} className="font-medium text-gray-500">
                {brand.emoji} {brand.name}
              </span>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}

export default Footer;