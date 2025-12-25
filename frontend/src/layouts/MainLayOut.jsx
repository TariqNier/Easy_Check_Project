import React from "react";
import { Outlet } from "react-router-dom";
import NavBar from "../components/common/NavBar";
import Footer from "../components/common/Footer";

function MainLayout() {
  return (
    <div className="flex flex-col min-h-screen">
      <NavBar />
      <main className="flex-1  flex flex-col items-center justify-center overflow-hidden">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}

export default MainLayout;
