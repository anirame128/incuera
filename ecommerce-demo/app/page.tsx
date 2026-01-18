'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'

interface Product {
  id: number
  name: string
  price: number
  image: string
  description: string
  category?: string
}

const products: Product[] = [
  {
    id: 1,
    name: 'Wireless Headphones',
    price: 99.99,
    image: '🎧',
    description: 'Premium noise-cancelling wireless headphones with 30-hour battery life',
    category: 'Audio',
  },
  {
    id: 2,
    name: 'Smart Watch',
    price: 249.99,
    image: '⌚',
    description: 'Fitness tracking smartwatch with heart rate monitor and GPS',
    category: 'Wearables',
  },
  {
    id: 3,
    name: 'Laptop Stand',
    price: 49.99,
    image: '💻',
    description: 'Ergonomic aluminum laptop stand with adjustable height',
    category: 'Accessories',
  },
  {
    id: 4,
    name: 'Mechanical Keyboard',
    price: 129.99,
    image: '⌨️',
    description: 'RGB backlit mechanical keyboard with Cherry MX switches',
    category: 'Accessories',
  },
  {
    id: 5,
    name: 'Wireless Mouse',
    price: 39.99,
    image: '🖱️',
    description: 'Ergonomic wireless mouse with precision tracking and long battery',
    category: 'Accessories',
  },
  {
    id: 6,
    name: 'USB-C Hub',
    price: 59.99,
    image: '🔌',
    description: 'Multi-port USB-C hub with HDMI output and fast charging',
    category: 'Accessories',
  },
]

export default function Home() {
  const router = useRouter()
  const [cart, setCart] = useState<{ product: Product; quantity: number }[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false)

  // Load cart from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('cart')
      if (saved) {
        setCart(JSON.parse(saved))
      }
    }
  }, [])

  // Save cart to localStorage whenever it changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('cart', JSON.stringify(cart))
    }
  }, [cart])

  const addToCart = (product: Product) => {
    setCart((prev) => {
      const existing = prev.find((item) => item.product.id === product.id)
      if (existing) {
        return prev.map((item) =>
          item.product.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        )
      }
      return [...prev, { product, quantity: 1 }]
    })
  }

  const removeFromCart = (productId: number) => {
    setCart((prev) => prev.filter((item) => item.product.id !== productId))
  }

  const updateQuantity = (productId: number, quantity: number) => {
    if (quantity <= 0) {
      removeFromCart(productId)
      return
    }
    setCart((prev) =>
      prev.map((item) =>
        item.product.id === productId ? { ...item, quantity } : item
      )
    )
  }

  const total = cart.reduce(
    (sum, item) => sum + item.product.price * item.quantity,
    0
  )

  const cartItemCount = cart.reduce((sum, item) => sum + item.quantity, 0)

  const filteredProducts = products.filter((product) =>
    product.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    product.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleCheckout = () => {
    setIsCheckoutOpen(true)
  }

  const handleCheckoutComplete = () => {
    setCart([])
    setIsCheckoutOpen(false)
  }

  const goToCheckout = () => {
    router.push('/checkout')
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
            <Link href="/" className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight">ShopHub</h1>
              <Badge variant="secondary" className="hidden sm:inline-flex">
                Demo
              </Badge>
            </Link>
          <div className="flex items-center gap-4">
            <div className="relative hidden sm:block">
              <Input
                type="text"
                placeholder="Search products..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-64"
              />
            </div>
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline" className="relative">
                  <span className="mr-2">🛒</span>
                  Cart
                  {cartItemCount > 0 && (
                    <Badge
                      variant="default"
                      className="absolute -right-2 -top-2 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
                    >
                      {cartItemCount}
                    </Badge>
                  )}
                </Button>
              </SheetTrigger>
              <SheetContent className="w-full sm:max-w-lg">
                <SheetHeader>
                  <SheetTitle>Shopping Cart</SheetTitle>
                  <SheetDescription>
                    {cart.length === 0
                      ? 'Your cart is empty'
                      : `${cartItemCount} item${cartItemCount !== 1 ? 's' : ''} in your cart`}
                  </SheetDescription>
                </SheetHeader>
                <Separator className="my-4" />
                {cart.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <div className="mb-4 text-6xl">🛒</div>
                    <p className="text-muted-foreground mb-2 text-lg font-medium">
                      Your cart is empty
                    </p>
                    <p className="text-muted-foreground text-sm">
                      Add some products to get started
                    </p>
                  </div>
                ) : (
                  <>
                    <ScrollArea className="h-[calc(100vh-280px)] pr-4">
                      <div className="space-y-4">
                        {cart.map((item) => (
                          <Card key={item.product.id}>
                            <CardContent className="p-4">
                              <div className="flex items-start gap-4">
                                <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-muted text-3xl">
                                  {item.product.image}
                                </div>
                                <div className="flex-1 space-y-1">
                                  <h3 className="font-semibold leading-none">
                                    {item.product.name}
                                  </h3>
                                  <p className="text-muted-foreground text-sm">
                                    ${item.product.price.toFixed(2)} each
                                  </p>
                                  <div className="flex items-center gap-2 pt-2">
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      onClick={() =>
                                        updateQuantity(
                                          item.product.id,
                                          item.quantity - 1
                                        )
                                      }
                                      className="h-8 w-8 p-0"
                                    >
                                      -
                                    </Button>
                                    <span className="w-12 text-center text-sm font-medium">
                                      {item.quantity}
                                    </span>
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      onClick={() =>
                                        updateQuantity(
                                          item.product.id,
                                          item.quantity + 1
                                        )
                                      }
                                      className="h-8 w-8 p-0"
                                    >
                                      +
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() =>
                                        removeFromCart(item.product.id)
                                      }
                                      className="ml-auto text-destructive hover:text-destructive"
                                    >
                                      Remove
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </ScrollArea>
                    <Separator className="my-4" />
                    <SheetFooter className="flex-col gap-2 sm:flex-row">
                      <div className="flex w-full flex-col gap-2">
                        <div className="flex items-center justify-between text-lg font-semibold">
                          <span>Total:</span>
                          <span>${total.toFixed(2)}</span>
                        </div>
                        <Button
                          className="w-full"
                          onClick={goToCheckout}
                        >
                          Proceed to Checkout
                        </Button>
                        <Dialog open={isCheckoutOpen} onOpenChange={setIsCheckoutOpen}>
                          <DialogTrigger asChild>
                            <Button
                              variant="outline"
                              className="w-full"
                              onClick={handleCheckout}
                            >
                              Review Order
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Checkout</DialogTitle>
                              <DialogDescription>
                                Review your order before completing the purchase
                              </DialogDescription>
                            </DialogHeader>
                            <div className="space-y-4 py-4">
                              <ScrollArea className="max-h-[300px]">
                                <div className="space-y-3">
                                  {cart.map((item) => (
                                    <div
                                      key={item.product.id}
                                      className="flex items-center justify-between rounded-lg border p-3"
                                    >
                                      <div className="flex items-center gap-3">
                                        <div className="flex h-12 w-12 items-center justify-center rounded bg-muted text-2xl">
                                          {item.product.image}
                                        </div>
                                        <div>
                                          <p className="font-medium">
                                            {item.product.name}
                                          </p>
                                          <p className="text-muted-foreground text-sm">
                                            Qty: {item.quantity}
                                          </p>
                                        </div>
                                      </div>
                                      <p className="font-semibold">
                                        $
                                        {(
                                          item.product.price * item.quantity
                                        ).toFixed(2)}
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              </ScrollArea>
                              <Separator />
                              <div className="flex items-center justify-between text-lg font-semibold">
                                <span>Total:</span>
                                <span>${total.toFixed(2)}</span>
                              </div>
                            </div>
                            <DialogFooter>
                              <Button
                                variant="outline"
                                onClick={() => setIsCheckoutOpen(false)}
                              >
                                Cancel
                              </Button>
                              <Button onClick={handleCheckoutComplete}>
                                Complete Order
                              </Button>
                            </DialogFooter>
                          </DialogContent>
                        </Dialog>
                      </div>
                    </SheetFooter>
                  </>
                )}
              </SheetContent>
            </Sheet>
          </div>
        </div>
        {/* Mobile Search */}
        <div className="container mx-auto border-t px-4 py-3 sm:hidden">
          <Input
            type="text"
            placeholder="Search products..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full"
          />
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Page Header */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold tracking-tight">
            {searchQuery
              ? `Search Results for "${searchQuery}"`
              : 'Featured Products'}
          </h2>
          <p className="text-muted-foreground mt-2">
            {searchQuery
              ? `Found ${filteredProducts.length} product${filteredProducts.length !== 1 ? 's' : ''}`
              : 'Discover our latest collection of premium products'}
          </p>
        </div>

        {/* Products Grid */}
        {filteredProducts.length === 0 ? (
          <Card className="py-12">
            <CardContent className="flex flex-col items-center justify-center text-center">
              <div className="mb-4 text-6xl">🔍</div>
              <CardTitle className="mb-2">No products found</CardTitle>
              <CardDescription>
                Try adjusting your search query or browse all products
              </CardDescription>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => setSearchQuery('')}
              >
                Clear Search
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {filteredProducts.map((product) => (
              <Link key={product.id} href={`/products/${product.id}`}>
                <Card
                  className="group flex h-full flex-col overflow-hidden transition-all hover:shadow-lg"
                >
                <div className="relative flex h-64 items-center justify-center bg-muted/50 transition-colors group-hover:bg-muted">
                  <span className="text-7xl transition-transform group-hover:scale-110">
                    {product.image}
                  </span>
                  {product.category && (
                    <Badge
                      variant="secondary"
                      className="absolute top-4 right-4"
                    >
                      {product.category}
                    </Badge>
                  )}
                </div>
                <CardHeader>
                  <CardTitle className="line-clamp-1">{product.name}</CardTitle>
                  <CardDescription className="line-clamp-2">
                    {product.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold">
                      ${product.price.toFixed(2)}
                    </span>
                  </div>
                </CardContent>
                <CardFooter>
                  <Button
                    className="w-full"
                    onClick={(e) => {
                      e.preventDefault()
                      addToCart(product)
                    }}
                  >
                    Add to Cart
                  </Button>
                </CardFooter>
              </Card>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
