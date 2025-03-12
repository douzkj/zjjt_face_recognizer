# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import sys
from codeformer.app import inference_app

if __name__ == "__main__":
    # if len(sys.argv) != 2:
    #     print("Usage: python program.py input_image_path")
    #     sys.exit(1)
    input_path = "visitor_face/visitor_visitor_1741689004286/visitor_visitor_1741689004286.jpg"
    output_path = "output.jpg"
    inference_app(image=input_path, background_enhance=False, face_upsample=True, upscale=1, codeformer_fidelity=0.5)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/

