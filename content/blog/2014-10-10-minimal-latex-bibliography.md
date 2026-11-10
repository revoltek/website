---
title: Minimal LaTeX bibliography
date: 2014-10-10
categories: [Coding, LaTeX]
---

I wanted to make a readable bibliography which uses as less space as possible, something like this:

![Compact bibliography](/media/ref.png)

I modified the A&A natbib style package to have something like that, [here](/media/bib.txt) is the code (rename bib.txt to proposal.bst). You need to put it into your latex as:

```latex
\usepackage[numbers, sort&compress]{natbib}
\bibliographystyle{proposal}
\usepackage{paralist}
\renewenvironment{thebibliography}[1]{
 \section*{\refname}
 \let\par\relax\let\newblock\relax
 \let\olditem\item
 \renewcommand{\item}[1][]{ \textbullet\ \textbf{\olditem} }
 \inparaenum}{\endinparaenum}
```

This create citations of the type “[1]”, which are the shortest. They are listed in order of appearance. To add the bibliography then I use:

```latex
{\footnotesize
\renewcommand{\section}[2]{} % remove title
\setlength{\bibsep}{0.0pt}
\bibliography{bib}
}
```
