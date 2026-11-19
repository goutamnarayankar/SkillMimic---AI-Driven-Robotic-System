
import streamlit as st
import cv2
import base64
import time

st.set_page_config(page_title="SkillMimic Camera Test")
st.title("SkillMimic - Camera Preview Test")

camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not camera.isOpened():
    st.error("Camera could not be opened.")
else:
    placeholder = st.empty()

    try:
        for _ in range(100):
            success, frame = camera.read()

            if not success:
                st.warning("Could not capture frame.")
                break

            frame = cv2.flip(frame, 1)
            encoded_ok, buffer = cv2.imencode(".jpg", frame)

            if encoded_ok:
                image_base64 = base64.b64encode(
                    buffer.tobytes()
                ).decode("utf-8")

                html = f"""
                <img
                    src="data:image/jpeg;base64,{image_base64}"
                    style="width:100%; border-radius:12px;"
                />
                """

                placeholder.markdown(
                    html,
                    unsafe_allow_html=True
                )

            time.sleep(0.05)

    finally:
        camera.release()
