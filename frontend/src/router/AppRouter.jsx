import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";

import AdminLayout from "../layouts/AdminLayout";
import MainLayout from "../layouts/MainLayOut";

import ProtectedRoute from "../router/ProtectedRoute";

import Home from "../pages/home/Home";
import ImeiChecker from "../pages/ImeiSearch/ImeiChecker";
import CheckResult from "../pages/ImeiSearch/CheckResult";

import PaymentSuccess from "../pages/payment/PaymentSuccess";
import PaymentFaild from "../pages/payment/PaymentFaild";

import AddBalance from "../pages/payment/AddBalance";
import SearchHistory from "../pages/user/SearchHistory";
import PaymentHistory from "../pages/user/PaymentHistory";

export const router = createBrowserRouter([
  // 🌍 1. Public Routes with MainLayout
  {
    element: <MainLayout />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/imei-checker", element: <ImeiChecker /> },
      { path: "/result/:id", element: <CheckResult /> },

      // 🔐 Protected Routes (User must be logged in)
      {
        element: <ProtectedRoute />,
        children: [
          { path: "/add-balance", element: <AddBalance /> },
          { path: "/search-history", element: <SearchHistory /> },
          { path: "/payment-history", element: <PaymentHistory /> },
        ],
      },
    ],
  },

  // 💳 2. Payment Routes (No Layout - Standalone Pages)

  {
    path: "/payment-success",
    element: <PaymentSuccess />,
  },
  {
    path: "/payment-failed",
    element: <PaymentFaild />,
  },


]);


function AppRouter() {
  return (
    <RouterProvider router={router} />
  )
}

export default AppRouter
