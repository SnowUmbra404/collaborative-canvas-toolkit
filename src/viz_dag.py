import os
import random
from PIL import Image, ImageDraw
from src.hashdag import Node
from src.core.render import _rgb, BG

def render_dag(nodes, path: str, *, size: int = 600, duration: int = 300) -> int:
    """Render the DAG growth as a GIF."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Simple topo layout
    # X: lamport level, Y: stack nodes
    node_list = sorted(nodes, key=lambda n: (n.lamport, n.id))
    
    frames = []
    
    # Layering
    layers = {}
    for n in node_list:
        l = n.lamport
        if l not in layers: layers[l] = []
        layers[l].append(n)
        
    for i in range(len(node_list)):
        img = Image.new("RGB", (size, size), BG)
        draw = ImageDraw.Draw(img)
        
        # Draw edges + nodes
        for j in range(i + 1):
            n = node_list[j]
            x = 50 + (n.lamport - 1) * 80
            y = 50 + layers[n.lamport].index(n) * 60
            
            # Edges
            for p_id in n.parents:
                p = next((n for n in node_list if n.id == p_id), None)
                if p:
                    px = 50 + (p.lamport - 1) * 80
                    py = 50 + layers[p.lamport].index(p) * 60
                    draw.line([px + 10, py + 10, x + 10, y + 10], fill=(150, 150, 150), width=2)
            
            # Nodes
            draw.ellipse([x, y, x + 20, y + 20], fill=_rgb("blue"), outline="black")
            draw.text((x + 5, y + 5), n.id[:4], fill="white")
            
        frames.append(img)
        
    # Final frame
    frames.append(frames[-1])
    
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=duration, loop=0)
    return len(frames)
