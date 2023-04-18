import matplotlib
import streamlit as st
from PIL import Image


@st.cache(hash_funcs={matplotlib.figure.Figure: lambda _: None})
def plot_fig(base_images, idx):
    im_base = Image.open(base_images[idx])
    dpi = 200
    margin = 0.05
    xpixels, ypixels = 1000, 2200
    mag = 2

    figsize = mag * (1 + margin) * ypixels / dpi, mag * (1 + margin) * xpixels / dpi

    fig = matplotlib.pyplot.figure(figsize=figsize, dpi=dpi)
    ax = fig.add_axes([margin, margin, 1 - 2 * margin, 1 - 2 * margin])
    ax.set_yticks(range(0, 2200, 50))
    ax.minorticks_on()
    ax.imshow(im_base, interpolation="none")
    return fig
