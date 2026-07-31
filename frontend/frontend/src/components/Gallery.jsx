import React from "react";

import PhotoCard from "./PhotoCard";

function Gallery({ photos }) {

    return (

        <div
            style={{
                display: "flex",
                flexWrap: "wrap",
                justifyContent: "center"
            }}
        >

            {

                photos.map(

                    (photo, index) => (

                        <PhotoCard

                            key={index}

                            photo={photo}

                        />

                    )

                )

            }

        </div>

    );

}

export default Gallery;