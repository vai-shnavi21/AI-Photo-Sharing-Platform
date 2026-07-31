import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Navbar from "./components/Navbar";

import Home from "./pages/Home";
import UploadPhotos from "./pages/UploadPhotos";
import UploadSelfie from "./pages/UploadSelfie";
import Results from "./pages/Results";

function App() {

    return (

        <BrowserRouter>

            <Navbar />

            <Routes>

                <Route
                    path="/"
                    element={<Home />}
                />

                <Route
                    path="/upload-event"
                    element={<UploadPhotos />}
                />

                <Route
                    path="/upload-selfie"
                    element={<UploadSelfie />}
                />

                <Route
                    path="/results"
                    element={<Results />}
                />

            </Routes>

        </BrowserRouter>

    );

}

export default App;