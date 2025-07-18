# cSpell:ignore agnoster, zstyle, strftime, dotenv, mvim, ohmyzsh, krew, zshell, CWORD, tldr, tealdeermusl, fpath, kubectx, kubens, trivy
# If you come from bash you might have to change your $PATH.
# export PATH=${HOME}/bin:/usr/local/bin:$PATH

# Path to your oh-my-zsh installation.
export ZSH=${HOME}/.oh-my-zsh

# Set name of the theme to load --- if set to "random", it will
# load a random theme each time oh-my-zsh is loaded, in which case,
# to know which specific one was loaded, run: echo $RANDOM_THEME
# See https://github.com/ohmyzsh/ohmyzsh/wiki/Themes
# We leave this commented out. If the user has this var set it will turn off the Starship theme and use the one given.
# ZSH_THEME="devcontainers"

# Set list of themes to pick from when loading at random
# Setting this variable when ZSH_THEME="devcontainers"
# a theme from this variable instead of looking in $ZSH/themes/
# If set to an empty array, this variable will have no effect.
# ZSH_THEME_RANDOM_CANDIDATES=( "robbyrussell" "agnoster" )

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

# Uncomment the following line to use hyphen-insensitive completion.
# Case-sensitive completion must be off. _ and - will be interchangeable.
# HYPHEN_INSENSITIVE="true"

# Uncomment one of the following lines to change the auto-update behavior
# zstyle ':omz:update' mode disabled  # disable automatic updates
# zstyle ':omz:update' mode auto      # update automatically without asking
# zstyle ':omz:update' mode reminder  # just remind me to update when it's time

# Uncomment the following line to change how often to auto-update (in days).
# zstyle ':omz:update' frequency 13

# Uncomment the following line if pasting URLs and other text is messed up.
# DISABLE_MAGIC_FUNCTIONS="true"

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

# Uncomment the following line to disable auto-setting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment the following line to enable command auto-correction.
# ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
# You can also set it to another string to have that shown instead of the default red dots.
# e.g. COMPLETION_WAITING_DOTS="%F{yellow}waiting...%f"
# Caution: this setting can cause issues with multiline prompts in zsh < 5.7.1 (see #5765)
# COMPLETION_WAITING_DOTS="true"

# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
# DISABLE_UNTRACKED_FILES_DIRTY="true"

# Uncomment the following line if you want to change the command execution time
# stamp shown in the history command output.
# You can set one of the optional three formats:
# "mm/dd/yyyy"|"dd.mm.yyyy"|"yyyy-mm-dd"
# or set a custom format using the strftime function format specifications,
# see 'man strftime' for details.
# HIST_STAMPS="mm/dd/yyyy"

# Would you like to use another custom folder than $ZSH/custom?
# ZSH_CUSTOM=/path/to/new-custom-folder

# Which plugins would you like to load?
# Standard plugins can be found in $ZSH/plugins/
# Custom plugins may be added to $ZSH_CUSTOM/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.

# Disable asking to load .env files.
export DOTENV_PROMPT=0

plugins=(
  zsh-autosuggestions
  fast-syntax-highlighting
  zsh-autocomplete
  zsh-completions
  aliases
  gitfast
  history
  kubectl
  python
  dotenv
  helm
  docker
  git
)

source $ZSH/oh-my-zsh.sh

# User configuration

# export MANPATH="/usr/local/man:$MANPATH"

# You may need to manually set your language environment
# export LANG=en_US.UTF-8

# Preferred editor for local and remote sessions
# if [[ -n $SSH_CONNECTION ]]; then
#   export EDITOR='vim'
# else
#   export EDITOR='mvim'
# fi

# Compilation flags
# export ARCHFLAGS="-arch x86_64"

# Set personal aliases, overriding those provided by oh-my-zsh libs,
# plugins, and themes. Aliases can be placed here, though oh-my-zsh
# users are encouraged to define aliases within the ZSH_CUSTOM folder.
# For a full list of active aliases, run `alias`.
#
# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"
DISABLE_AUTO_UPDATE=true
DISABLE_UPDATE_PROMPT=true

##### Begin User Modifications
# Set up bash history to work with the passed in Docker volume
export PROMPT_COMMAND='history -a' &&
  export HISTFILE=/commandhistory/.bash_history

export PATH="${HOME}/.krew/bin:${HOME}/.local:${HOME}/.local/bin:${HOME}/.local/share:${HOME}/.local/share/mise/shims:${HOME}/bin:${HOME}/.linkerd2/bin:${PATH}"

# Following command is needed for terraform, vault, packer and maybe others in zshell
autoload -U +X bashcompinit && bashcompinit

export EDITOR="nano"

# List files colors and aliases
export LS_COLORS=$LS_COLORS:"ow=0;32:"
# alias ls to lsd, the colorful ls replacement
alias ls='lsd'
alias ll='ls -alh'
alias la='ls -A'

# Docker
alias d="docker"

# Kubernetes
alias a="argocd"
alias k="k9s"
alias kc="kubectl"
alias kx="kubectx"
alias kn="kubens"
alias l="linkerd"
alias h="helm"

# Starship
if [[ -z "${ZSH_THEME}" ]]; then
  eval "$(starship init zsh)"
fi

# Hashicorp
alias tf="tofu"
complete -o nospace -C tofu tofu tf
alias v="vault"
complete -C vault vault v
alias p="packer"
complete -o nospace -C packer packer p

# Utils
alias help="/usr/local/bin/help"
alias g=git

fpath=($ZSH/custom/completions $fpath)

# Add fzf auto completions and key bindings
source "${HOME}/.fzf-key-bindings.zsh"
source "${HOME}/.fzf-completion.zsh"

# Active mise
if command -v mise &>/dev/null; then
  # Only activate mise if installation is complete to avoid warnings
  eval "$(/usr/local/bin/mise activate zsh 2>/dev/null)"
  # Add mise shims to PATH manually for basic functionality
  export PATH="${HOME}/.local/share/mise/shims:$PATH"
fi

# Activate zoxide
if command -v zoxide &>/dev/null; then
  eval "$(zoxide init zsh --cmd cd)"
fi

help
