import React from "react";
import { Search, ChevronRight } from "lucide-react";

function HeroSection({ onSearchClick }) {
  return (
    <>
      {/* Main Heading */}
      <h1 className="text-4xl md:text-5xl lg:text-7xl font-black text-dark mb-4 sm:mb-6 leading-tight px-4">
        Verify Device
        <br />
        <div className="flex flex-row justify-center gap-2 text-main-green mt-2">
          <span>Authenticity</span>
          <span className="relative">
            Instantly
            <svg
              className="absolute -bottom-2 left-0 w-full h-3 text-lime-yellow"
              viewBox="0 0 200 12"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M2 6C50 2 150 2 198 6"
                stroke="currentColor"
                strokeWidth="4"
                strokeLinecap="round"
              />
            </svg>
          </span>
        </div>
      </h1>

      {/* Description */}
      <p className="max-w-2xl mx-auto text-sm sm:text-base lg:text-lg text-main-green mb-8 sm:mb-12 leading-relaxed px-4">
        The most reliable tool to check blacklist status, warranty, carrier
        lock, and model details for any device. Fast, accurate, and secure
        analysis.
      </p>

      {/* CTA Button */}
      <button
        onClick={onSearchClick}
        className="group inline-flex items-center gap-2 sm:gap-3 px-6 sm:px-8 py-3 sm:py-4 bg-lime-yellow  text-dark text-base sm:text-lg font-bold rounded-xl hover:bg-[#d4ea23] transition-all shadow-lg hover:shadow-xl hover:scale-105 active:scale-95"
      >
        <Search className="w-4 h-4 sm:w-5 sm:h-5" />
        <span className="hidden sm:inline">Go to IMEI Search Page</span>
        <span className="sm:hidden">Search IMEI</span>
        <ChevronRight className="w-4 h-4 sm:w-5 sm:h-5 group-hover:translate-x-1 transition-transform" />
      </button>
    </>
  );
}

export default HeroSection;
