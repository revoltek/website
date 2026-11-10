---
title: LaTeX Figure with caption and many images
date: 2012-05-11
categories: [Coding, LaTeX]
---

Here is the LaTeX code to insert two images of different dimensions and a caption in this format:

![Layout of the figure](/media/caption.png)

The code uses minipages (as usual!) to solve this problem.

```latex
\begin{figure*}
 \begin{minipage}[t]{.6\linewidth}\vspace{0pt}
  \includegraphics[width=\linewidth]{image1.eps}
  \label{fig:image1}
 \end{minipage}
 \hfill
 \begin{minipage}[t]{.4\linewidth}\vspace{0pt}\raggedright
  \begin{minipage}[t]{\linewidth}\vspace{0pt}\raggedright
   \includegraphics[width=\linewidth]{image2.eps}
   \label{fig:image2}
  \end{minipage}
  \begin{minipage}[t]{\linewidth}\vspace{20pt}\raggedright
   \caption{Caption [...]}
   \label{fig:spidx}
  \end{minipage}
 \end{minipage}
\end{figure*}
```
