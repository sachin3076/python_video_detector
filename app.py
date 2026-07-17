import os
import cv2
import streamlit as st
from ultralytics import YOLO
from collections import Counter

# Load the pre-trained YOLOv8 model
@st.cache_resource
def load_model():
    return YOLO('yolov8n.pt')

model = load_model()

# Helper function 1: AI ko image dikhana
def analyze_frame(frame, model):
    results = model(frame, verbose=False)
    
    current_status = "Empty (Ground Khali hai)"
    current_color = "red"
    persons = 0
    sports_items = 0
    
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            if cls_id == 0:
                persons += 1
            elif cls_id in [32, 34]: 
                sports_items += 1
                
    if persons > 0:
        if sports_items > 0 or persons > 3:
            current_status = "Playing (Log Cricket Khel Rahe Hain)"
            current_color = "green"
        else:
            current_status = "Cleaning / Idle (Log hain par khel nahi rahe - Safai ho sakti hai)"
            current_color = "orange"
            
    annotated_frame = results[0].plot()
    annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
    
    return annotated_frame, current_status, current_color

# Helper function 2: 30 Second wala Batch Logic (Single Video)
def run_analysis(cap, frame_placeholder, status_placeholder, interval_seconds=30):
    status_history = []
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0: fps = 30
    
    interval_frames = int(fps * interval_seconds)
    frame_count = 0
    
    last_published_status = "Waiting for 30s of data..."
    last_published_color = "gray"
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
            
        frame_count += 1
        annotated_frame, status, color = analyze_frame(frame, model)
        status_history.append((status, color))
        
        frame_placeholder.image(annotated_frame, channels="RGB")
        
        frames_left = interval_frames - (frame_count % interval_frames)
        seconds_left = int(frames_left / fps)
        
        if frame_count % interval_frames == 0:
            batch = status_history[-interval_frames:]
            most_common = Counter([s[0] for s in batch]).most_common(1)[0][0]
            for s, c in batch:
                if s == most_common:
                    last_published_color = c
                    break
            last_published_status = most_common
            
        status_text = f"<div style='padding:10px; border-radius:5px; background:#222; border: 1px solid #444;'><p style='margin:0; font-size:14px; color:#bbb;'>🕒 Simulation: Next Update in {seconds_left}s...</p><h3 style='margin:5px 0 0 0; color:{last_published_color};'>{last_published_status}</h3></div>"
        status_placeholder.markdown(status_text, unsafe_allow_html=True)
        
    if len(status_history) > 0:
        most_common = Counter([s[0] for s in status_history]).most_common(1)[0][0]
        for s, c in status_history:
            if s == most_common:
                last_published_color = c
                break
        status_placeholder.markdown(f"<div style='padding:10px; border-radius:5px; background:#222; border: 1px solid #444;'><p style='margin:0; font-size:14px; color:#bbb;'>✅ Video Ended - Final Output (Sent to Server)</p><h3 style='margin:5px 0 0 0; color:{last_published_color};'>{most_common}</h3></div>", unsafe_allow_html=True)

# Helper function 3: Dono videos ke liye ek sath 30-sec logic
def run_analysis_both(cap1, fp1, sp1, cap2, fp2, sp2, interval_seconds=30):
    status_history1 = []
    status_history2 = []
    
    fps = cap1.get(cv2.CAP_PROP_FPS) or 30
    interval_frames = int(fps * interval_seconds)
    frame_count = 0
    
    last_stat1, last_col1 = "Waiting for data...", "gray"
    last_stat2, last_col2 = "Waiting for data...", "gray"
    
    while cap1.isOpened() or cap2.isOpened():
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()
        
        if not ret1 and not ret2:
            break
            
        frame_count += 1
        
        if ret1:
            a_frame1, stat1, col1 = analyze_frame(frame1, model)
            status_history1.append((stat1, col1))
            fp1.image(a_frame1, channels="RGB")
        if ret2:
            a_frame2, stat2, col2 = analyze_frame(frame2, model)
            status_history2.append((stat2, col2))
            fp2.image(a_frame2, channels="RGB")
            
        frames_left = interval_frames - (frame_count % interval_frames)
        sec_left = int(frames_left / fps)
        
        if frame_count % interval_frames == 0:
            if ret1 and status_history1:
                b1 = status_history1[-interval_frames:]
                last_stat1 = Counter([s[0] for s in b1]).most_common(1)[0][0]
                last_col1 = next((c for s, c in b1 if s == last_stat1), "red")
            if ret2 and status_history2:
                b2 = status_history2[-interval_frames:]
                last_stat2 = Counter([s[0] for s in b2]).most_common(1)[0][0]
                last_col2 = next((c for s, c in b2 if s == last_stat2), "red")
                
        html = "<div style='padding:10px; border-radius:5px; background:#222; border: 1px solid #444;'><p style='margin:0; font-size:14px; color:#bbb;'>🕒 Next Update in {s}s...</p><h3 style='margin:5px 0 0 0; color:{c};'>{stat}</h3></div>"
        
        if ret1: sp1.markdown(html.format(s=sec_left, c=last_col1, stat=last_stat1), unsafe_allow_html=True)
        if ret2: sp2.markdown(html.format(s=sec_left, c=last_col2, stat=last_stat2), unsafe_allow_html=True)


st.title("🏏 Cricket Ground Status Analyzer (Production Mode)")
st.write("Ab ye system real production ki tarah har 30 second ke data ko ikattha karega aur ek solid result dega.")

if not os.path.exists("assets"):
    os.makedirs("assets")

video_files = [f for f in os.listdir("assets") if f.endswith(('.mp4', '.avi', '.mov'))]

if len(video_files) >= 2:
    st.write("📂 Dono videos yaha hain:")
    
    video1_path = os.path.join("assets", video_files[0])
    video2_path = os.path.join("assets", video_files[1])
    
    # Naya Button Jo Dono Ek Sath Chalayega
    if st.button("🚀 Analyze BOTH Videos Simultaneously (30s batch)"):
        col1, col2 = st.columns(2)
        with col1:
            st.video(video1_path)
            fp1 = st.empty()
            sp1 = st.empty()
        with col2:
            st.video(video2_path)
            fp2 = st.empty()
            sp2 = st.empty()
            
        st.write("Dono videos ek sath analyze ho rahi hain... Please wait.")
        cap1 = cv2.VideoCapture(video1_path)
        cap2 = cv2.VideoCapture(video2_path)
        run_analysis_both(cap1, fp1, sp1, cap2, fp2, sp2, interval_seconds=30)
        if cap1.isOpened(): cap1.release()
        if cap2.isOpened(): cap2.release()
        st.success("✅ Analysis Complete!")
        
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.video(video1_path)
                
        with col2:
            st.video(video2_path)

elif len(video_files) == 1:
    video_path = os.path.join("assets", video_files[0])
    st.video(video_path)
    if st.button("🔍 Analyze Video (30s batch)"):
        cap = cv2.VideoCapture(video_path)
        fp = st.empty()
        sp = st.empty()
        run_analysis(cap, fp, sp, interval_seconds=30)
        cap.release()
        st.success("✅ Analysis Complete!")

else:
    st.error("Assets folder mein koi video nahi mili! Kripya apni dono videos ko VS Code mein 'assets' folder ke andar copy kar dein.")
