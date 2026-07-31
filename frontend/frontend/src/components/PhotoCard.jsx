import React from "react";

function PhotoCard({ photo }) {

    return (

        <div
            style={{
                border: "1px solid gray",
                padding: "10px",
                margin: "15px",
                width: "280px"
            }}
        >

            <img

                src={`http://127.0.0.1:8000/uploads/event_photos/${photo.photo}`}

                alt=""

                width="250"

            />

            <h4>{photo.photo}</h4>

            <p>

                Similarity :

                {photo.similarity}

            </p>

        </div>

    );

}

export default PhotoCard;