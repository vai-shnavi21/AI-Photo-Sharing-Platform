import React from "react";
import { useLocation } from "react-router-dom";
import Gallery from "../components/Gallery";

function Results() {
    const location = useLocation();
    const photos = location.state?.photos || [];

    return (
        <main className="content-shell results-page">
            <section className="page-card">
                <div className="page-heading">
                    <div>
                        <p className="eyebrow">MATCHED PHOTOS</p>
                        <h1>Face match results</h1>
                        <p className="muted">Browse the photos from your event that best match your selfie.</p>
                    </div>
                </div>
                {photos.length === 0 ? (
                    <section className="empty-gallery">
                        <div>🔎</div>
                        <h2>No matches found</h2>
                        <p>Try uploading a clearer selfie or a different angle.</p>
                    </section>
                ) : (
                    <Gallery photos={photos} />
                )}
            </section>
        </main>
    );
}

export default Results;