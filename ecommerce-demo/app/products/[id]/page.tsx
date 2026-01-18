'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { ArrowLeft, ShoppingCart, Plus, Minus } from 'lucide-react'

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

export default function ProductDetailPage() {
  const params = useParams()
  const router = useRouter()
  const productId = parseInt(params.id as string)
  const product = products.find((p) => p.id === productId)
  const [quantity, setQuantity] = useState(1)
  const [cart, setCart] = useState<{ product: Product; quantity: number }[]>([])

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('cart')
      if (saved) {
        setCart(JSON.parse(saved))
      }
    }
  }, [])

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('cart', JSON.stringify(cart))
    }
  }, [cart])

  if (!product) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-16 sm:px-6 lg:px-8">
          <Card className="mx-auto max-w-2xl">
            <CardHeader>
              <CardTitle>Product Not Found</CardTitle>
              <CardDescription>
                The product you're looking for doesn't exist.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild>
                <Link href="/">Back to Shop</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  const addToCart = () => {
    const existing = cart.find((item) => item.product.id === product.id)
    if (existing) {
      setCart((prev) =>
        prev.map((item) =>
          item.product.id === product.id
            ? { ...item, quantity: item.quantity + quantity }
            : item
        )
      )
    } else {
      setCart((prev) => [...prev, { product, quantity }])
    }
    router.push('/')
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-2">
            <ArrowLeft className="h-4 w-4" />
            <span className="text-sm font-medium">Back to Shop</span>
          </Link>
          <Link href="/" className="text-xl font-bold">
            ShopHub
          </Link>
          <div className="w-24" />
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid gap-8 lg:grid-cols-2">
          {/* Product Image */}
          <div className="flex items-center justify-center rounded-lg bg-muted/50 p-12">
            <span className="text-9xl">{product.image}</span>
          </div>

          {/* Product Details */}
          <div className="space-y-6">
            <div>
              {product.category && (
                <Badge variant="secondary" className="mb-2">
                  {product.category}
                </Badge>
              )}
              <h1 className="text-4xl font-bold tracking-tight">
                {product.name}
              </h1>
              <p className="text-muted-foreground mt-2 text-lg">
                {product.description}
              </p>
            </div>

            <Separator />

            <div>
              <p className="text-4xl font-bold">${product.price.toFixed(2)}</p>
              <p className="text-muted-foreground text-sm">
                Free shipping on orders over $50
              </p>
            </div>

            <Separator />

            {/* Quantity Selector */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Quantity</label>
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                >
                  <Minus className="h-4 w-4" />
                </Button>
                <span className="w-12 text-center text-lg font-medium">
                  {quantity}
                </span>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setQuantity(quantity + 1)}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Add to Cart Button */}
            <Button
              className="w-full"
              size="lg"
              onClick={addToCart}
            >
              <ShoppingCart className="mr-2 h-5 w-5" />
              Add to Cart
            </Button>

            {/* Product Features */}
            <Card>
              <CardHeader>
                <CardTitle>Product Features</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span className="text-sm">Premium quality materials</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span className="text-sm">30-day money-back guarantee</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span className="text-sm">Free shipping on orders over $50</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span className="text-sm">1-year warranty included</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
