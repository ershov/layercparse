
func(5,6);

return func(5,6);

int x;

/* pre */
int *x; /* post */

a;

a, b;

*a;

*a, *b;

x = 5 + 8;

int x = 5 + 8;

/* comment */
/*
 * block comment
 */

// Preprocessor

/* pre comment */
#define qwe QWE /* post comment */

#define asd(x, y) ASD \
  ZXC /* post comment */

// typedef

/* pre comment */
typedef aa bbb; /* post comment */

/* pre comment */
typedef TAILQ_HEAD(aa,bb) tqh; /* post comment */

// records

/* pre comment */
struct {
  /* pre comment 2 */
  int a, b; /* post comment 2 */
  char c;
}; /* post comment */

/* pre comment */
struct aaa {
  /* pre comment 2 */
  int a, b; /* post comment 2 */
  char c;
}; /* post comment */

/* pre comment */
struct {
  /* pre comment 2 */
  int a, b; /* post comment 2 */
  char c;
} bbb; /* post comment */

/* pre comment */
struct aaa {
  /* pre comment 2 */
  int a, b; /* post comment 2 */
  char c;
} bbb, ccc; /* post comment */

/* pre comment */
typedef struct aaa {
  /* pre comment 2 */
  int a, b; /* post comment 2 */
  char c;
} bbb, ccc; /* post comment */

/* pre comment */
union aaa {
  /* pre comment 2 */
  int a, b; /* post comment 2 */
  char c;
} bbb, ccc; /* post comment */

/* pre comment */
typedef enum aaa {
  AAA, BBB, CCC
} bbb, ccc; /* post comment */

/* pre comment */
typedef enum aaa {
  AAA, BBB, CCC
} bbb, ccc; /* post comment */

/* pre comment */
typedef union aaa {
  /* pre comment 2 */
  int a, b; /* post comment 2 */
  struct aaabbb {
    int bbb;
    struct aaabbbccc {
      int ccc;
    } yyy;
  } xxx;
  char c;
} bbb, ccc; /* post comment */

/* pre comment */
typedef union aaa {
  /* pre comment 2 */
  int a, b; /* post comment 2 */
  struct {
    int bbb;
    struct {
      int ccc;
    } yyy;
  } xxx;
  char c;
} bbb, ccc; /* post comment */

int func(int a, int b);
extern void func(int a, int b) __attribute__((__noreturn__));
extern inline void func(int a, int b) __attribute__((__noreturn__));
extern WT_INLINE void func(int a, int b) __attribute__((__noreturn__));
extern void func_of_ptr(int *a[100]) {
}

/*
 * func --
 *      function description
 */
int func(int a, int b) {
  int x;
  x = a + b;
  return (x);
}

do {
} while (0);


extern "C" {
  int func(int a, int b);
}


