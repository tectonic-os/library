# The toolkit registers its libraries in ld.so.conf.d.
# Only its tools need an entry on the login shell PATH.
case ":${PATH}:" in
    *:/usr/local/cuda/bin:*) ;;
    *) PATH="${PATH}:/usr/local/cuda/bin" ;;
esac
