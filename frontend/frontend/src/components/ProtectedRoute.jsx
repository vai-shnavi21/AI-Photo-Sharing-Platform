import React from "react";
import { Navigate } from "react-router-dom";
import { session } from "../services/auth";

function ProtectedRoute({ element }) {
  const user = session();
  return user ? element : <Navigate to="/signin" replace />;
}

export default ProtectedRoute;
