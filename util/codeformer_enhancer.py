
import subprocess
CODEFORMER_PATH="/data/CodeFormer"
CODEFORMER_INFERENCE_SCRIPT = "/data/CodeFormer/inference_codeformer.py"
VENV_PATH="/data/douzkj/face_recognizer/server/venv"

# 使用subprogress执行导出命令
def enhance(input_path,
            output_path,
            upscale=2,
            fidelity_weight=0.5,
            has_aligned=False,
            only_center_face=False,
            draw_box=False,
            detection_model='retinaface_resnet50',
            bg_upsampler=False,
            face_upsample=True,
            bg_tile=400,
            suffix=None,
            save_video_fps=None):
    command_str = f"""
    source {VENV_PATH}/bin/activate && 
    cd {CODEFORMER_PATH} && 
    python3 {CODEFORMER_INFERENCE_SCRIPT}  --input_path {input_path} --output_path {output_path} -w {fidelity_weight} --upscale {upscale} --bg_upsampler {bg_upsampler}
    """

    print(f"enhance command: {command_str}")

    # 在 subprocess 中执行激活虚拟环境和 CodeFormer 命令
    try:
        # 激活虚拟环境
        # subprocess.run(activate_cmd, shell=True, check=True)
        # print("运行虚拟环境成果！")
        # subprocess.run(f"cd {CODEFORMER_PATH}", shell=True, check=True)
        # print(f"进入{CODEFORMER_PATH} 目录")
        # 执行 CodeFormer 命令
        result = subprocess.run(command_str, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("CodeFormer 执行成功！")
            print(result.stdout)
            return True, result.stdout
        else:
            print("CodeFormer 执行失败！")
            print(result.stderr)
            return False, result.stderr
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")


if __name__ == '__main__':
    enhance(input_path="/data/douzkj/face_recognizer/server/FaceIdentyMan/visitor_face/visitor_visitor_1741689004286/visitor_visitor_1741689004286.jpg",
            output_path="/data/douzkj/face_recognizer/server/FaceIdentifyMan/out/output.jpg")


