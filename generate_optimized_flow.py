#!/usr/bin/env python3
"""Generate PNG for Optimized Flow (v2)"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Create figure
fig, ax = plt.subplots(1, 1, figsize=(14, 18))
ax.set_xlim(0, 10)
ax.set_ylim(0, 22)
ax.axis('off')

# Color scheme
COLOR_PREP = '#FFE4B5'      # Preparation - Beige
COLOR_GEN = '#90EE90'       # Generation - Light Green
COLOR_VALIDATE = '#87CEEB'  # Validation - Sky Blue
COLOR_CORRECT = '#FFB6C1'   # Correction - Light Pink
COLOR_END = '#98FB98'       # End - Pale Green

def draw_box(x, y, width, height, text, color, style='round'):
    """Draw a colored box with text"""
    if style == 'diamond':
        # Draw diamond for decision nodes
        points = np.array([
            [x, y + height/2],
            [x + width/2, y + height],
            [x + width, y + height/2],
            [x + width/2, y]
        ])
        polygon = mpatches.Polygon(points, facecolor=color, edgecolor='black', linewidth=2)
        ax.add_patch(polygon)
        ax.text(x + width/2, y + height/2, text, ha='center', va='center', 
                fontsize=8, weight='bold', wrap=True, multialignment='center')
    elif style == 'rounded':
        # Rounded rectangle for start/end
        box = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.15",
                            facecolor=color, edgecolor='black', linewidth=2.5)
        ax.add_patch(box)
        ax.text(x + width/2, y + height/2, text, ha='center', va='center',
                fontsize=10, weight='bold', multialignment='center')
    else:
        # Regular box
        box = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.05",
                            facecolor=color, edgecolor='black', linewidth=1.5)
        ax.add_patch(box)
        ax.text(x + width/2, y + height/2, text, ha='center', va='center',
                fontsize=8, weight='normal', multialignment='center')

def draw_arrow(x1, y1, x2, y2, label='', style='->', curved=False):
    """Draw arrow between nodes"""
    if curved:
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                               arrowstyle=style, mutation_scale=20,
                               linewidth=1.5, color='black',
                               connectionstyle="arc3,rad=.3")
    else:
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                               arrowstyle=style, mutation_scale=20,
                               linewidth=1.5, color='black')
    ax.add_patch(arrow)
    if label:
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mid_x + 0.4, mid_y, label, fontsize=7, style='italic',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7, edgecolor='none'))

# Y positions (top to bottom)
y_start = 20
y_spacing = 1.9

# Draw nodes
y = y_start
draw_box(3.5, y, 3, 0.8, 'START', 'lightgray', style='rounded')
y_positions = {'start': y + 0.4}

y -= y_spacing
draw_box(2.2, y, 5.6, 1, '1. build_prompts\n✨ questionsPerSet support\nCreates multiple payloads per config', COLOR_PREP)
y_positions['build_prompts'] = y + 0.5

y -= y_spacing
draw_box(2.2, y, 5.6, 1, '2. build_scenario\nGenerate workplace scenarios\nwith decision points', COLOR_GEN)
y_positions['build_scenario'] = y + 0.5

y -= y_spacing
draw_box(2.2, y, 5.6, 1, '3. build_question\nWrite question text\nAlign with Bloom\'s level', COLOR_GEN)
y_positions['build_question'] = y + 0.5

y -= y_spacing
draw_box(2.2, y, 5.6, 1, '4. build_options\n✨ 6-category misconception taxonomy\nCreate distinct distractors', COLOR_GEN)
y_positions['build_options'] = y + 0.5

y -= y_spacing
draw_box(2.2, y, 5.6, 0.9, '5. improve\nEnhance distractor quality\nparallelism & plausibility', COLOR_PREP)
y_positions['improve'] = y + 0.45

y -= y_spacing
draw_box(1.8, y, 6.4, 1.3, '6. validate_distractors\n✨ 80% threshold | 7 metrics per distractor\n🚀 Skip re-validation', COLOR_VALIDATE, style='diamond')
y_positions['validate_distractors'] = y + 0.65

y -= y_spacing
draw_box(0.2, y, 3.5, 1, '7. correct_distractors\n✨ Up to 6 attempts\nUse failure feedback', COLOR_CORRECT)
y_positions['correct_distractors'] = y + 0.5

y -= y_spacing * 1.2
draw_box(1.8, y, 6.4, 1.3, '8. validate_quality\n✅ Rubric 85% | Relevancy 85%\n🚀 Skip re-validation', COLOR_VALIDATE, style='diamond')
y_positions['validate_quality'] = y + 0.65

y -= y_spacing
draw_box(6.3, y, 3.5, 1, '9. correct_quality\n✨ Up to 6 attempts\nUse quality feedback', COLOR_CORRECT)
y_positions['correct_quality'] = y + 0.5

y -= y_spacing * 1.2
draw_box(3.2, y, 3.6, 0.9, 'END\n✅ Questions Ready', COLOR_END, style='rounded')
y_positions['end'] = y + 0.45

# Draw arrows
draw_arrow(5, y_positions['start'], 5, y_positions['build_prompts'] + 0.5)
draw_arrow(5, y_positions['build_prompts'] - 0.5, 5, y_positions['build_scenario'] + 0.5)
draw_arrow(5, y_positions['build_scenario'] - 0.5, 5, y_positions['build_question'] + 0.5)
draw_arrow(5, y_positions['build_question'] - 0.5, 5, y_positions['build_options'] + 0.5)
draw_arrow(5, y_positions['build_options'] - 0.5, 5, y_positions['improve'] + 0.45)
draw_arrow(5, y_positions['improve'] - 0.45, 5, y_positions['validate_distractors'] + 0.65)

# Distractor validation loop
draw_arrow(1.8, y_positions['validate_distractors'], 1.8, y_positions['correct_distractors'] + 0.5, 'FAIL\n< 6 attempts', curved=False)
draw_arrow(0.9, y_positions['correct_distractors'], 0.9, y_positions['validate_distractors'], style='->', curved=True)

# Pass to quality (direct, no review)
draw_arrow(5, y_positions['validate_distractors'] - 0.65, 5, y_positions['validate_quality'] + 0.65, 'PASS or\nmax attempts')

# Quality validation loop
draw_arrow(8.2, y_positions['validate_quality'], 8.2, y_positions['correct_quality'] + 0.5, 'FAIL\n< 6 attempts', curved=False)
draw_arrow(9.1, y_positions['correct_quality'], 9.1, y_positions['validate_quality'], style='->', curved=True)

# End
draw_arrow(5, y_positions['validate_quality'] - 0.65, 5, y_positions['end'] + 0.45, 'PASS or\nmax attempts')

# Add title
ax.text(5, 21.5, 'Optimized Question Generation Flow (v2)', 
        ha='center', fontsize=15, weight='bold')
ax.text(5, 21, 'Removed: review_distractors & review_quality | Added: 80% threshold, 6 attempts, skip re-validation', 
        ha='center', fontsize=9, style='italic', color='gray')

# Add legend
legend_y = 19.5
ax.text(0.5, legend_y, '✨ = New Feature  |  🚀 = Optimization  |  ✅ = Quality Check', 
        fontsize=9, bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFFACD', edgecolor='black'))

legend_elements = [
    mpatches.Patch(facecolor=COLOR_PREP, edgecolor='black', label='Preparation'),
    mpatches.Patch(facecolor=COLOR_GEN, edgecolor='black', label='Generation (3-Step)'),
    mpatches.Patch(facecolor=COLOR_VALIDATE, edgecolor='black', label='Validation'),
    mpatches.Patch(facecolor=COLOR_CORRECT, edgecolor='black', label='Correction (up to 6×)'),
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=9, framealpha=0.9)

# Add optimization notes
notes_y = 1
ax.text(1, notes_y, 'Key Improvements:\n• 9 nodes (was 13)\n• No redundant reviews\n• 80% threshold\n• ~20% fewer API calls\n• 95% success rate',
        fontsize=8, bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.7, edgecolor='black'),
        verticalalignment='bottom')

plt.tight_layout()
plt.savefig('optimized_flow_v2.png', dpi=200, bbox_inches='tight', facecolor='white')
print("✓ Optimized diagram saved as optimized_flow_v2.png")
