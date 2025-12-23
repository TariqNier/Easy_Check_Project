
import React from "react";
import { useNavigate } from "react-router-dom";
import HeroSection from "../../features/home/Herosection";
import FeaturePills from "../../features/home/Featurepills";


function Home() {
  const navigate = useNavigate();

  const handleSearchClick = () => {
    navigate("/imei-checker");
  };

  return (
    <section className=" md:py-10 px-4 sm:px-6 lg:px-8  flex items-center min-h-full">
      <div className="max-w-7xl mx-auto text-center w-full">
        <HeroSection onSearchClick={handleSearchClick} />
        <FeaturePills />
      </div>
    </section>
  );
}

export default Home;