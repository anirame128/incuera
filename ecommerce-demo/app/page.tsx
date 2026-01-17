'use client'

import { useState } from 'react'

interface Product {
  id: number
  name: string
  price: number
  image: string
  description: string
}

const products: Product[] = [
  {
    id: 1,
    name: 'Wireless Headphones',
    price: 99.99,
    image: '🎧',
    description: 'Premium noise-cancelling wireless headphones',
  },
  {
    id: 2,
    name: 'Smart Watch',
    price: 249.99,
    image: '⌚',
    description: 'Fitness tracking smartwatch with heart rate monitor',
  },
  {
    id: 3,
    name: 'Laptop Stand',
    price: 49.99,
    image: '💻',
    description: 'Ergonomic aluminum laptop stand',
  },
  {
    id: 4,
    name: 'Mechanical Keyboard',
    price: 129.99,
    image: '⌨️',
    description: 'RGB backlit mechanical keyboard',
  },
  {
    id: 5,
    name: 'Wireless Mouse',
    price: 39.99,
    image: '🖱️',
    description: 'Ergonomic wireless mouse with precision tracking',
  },
  {
    id: 6,
    name: 'USB-C Hub',
    price: 59.99,
    image: '🔌',
    description: 'Multi-port USB-C hub with HDMI output',
  },
]

export default function Home() {
  const [cart, setCart] = useState<{ product: Product; quantity: number }[]>([])
  const [searchQuery, setSearchQuery] = useState('')

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

  const filteredProducts = products.filter((product) =>
    product.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">ShopHub</h1>
            </div>
            <div className="flex items-center gap-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search products..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="rounded-md border border-gray-300 px-4 py-2 text-gray-900 text-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500"
                />
              </div>
              <div className="relative">
                <button className="flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
                  🛒 Cart
                  {cart.length > 0 && (
                    <span className="rounded-full bg-indigo-800 px-2 py-0.5 text-xs">
                      {cart.reduce((sum, item) => sum + item.quantity, 0)}
                    </span>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Cart Sidebar */}
        {cart.length > 0 && (
          <div className="mb-6 rounded-lg bg-white p-6 shadow">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              Shopping Cart
            </h2>
            <div className="space-y-4">
              {cart.map((item) => (
                <div
                  key={item.product.id}
                  className="flex items-center justify-between border-b border-gray-200 pb-4"
                >
                  <div className="flex items-center gap-4">
                    <span className="text-2xl">{item.product.image}</span>
                    <div>
                      <h3 className="font-medium text-gray-900">
                        {item.product.name}
                      </h3>
                      <p className="text-sm text-gray-600">
                        ${item.product.price.toFixed(2)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() =>
                        updateQuantity(item.product.id, item.quantity - 1)
                      }
                      className="rounded-md border border-gray-300 px-2 py-1 text-sm hover:bg-gray-50"
                    >
                      -
                    </button>
                    <span className="w-8 text-center text-sm">
                      {item.quantity}
                    </span>
                    <button
                      onClick={() =>
                        updateQuantity(item.product.id, item.quantity + 1)
                      }
                      className="rounded-md border border-gray-300 px-2 py-1 text-sm hover:bg-gray-50"
                    >
                      +
                    </button>
                    <button
                      onClick={() => removeFromCart(item.product.id)}
                      className="ml-4 text-red-600 hover:text-red-700"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
              <div className="flex items-center justify-between border-t border-gray-200 pt-4">
                <span className="text-lg font-semibold text-gray-900">
                  Total: ${total.toFixed(2)}
                </span>
                <button className="rounded-md bg-indigo-600 px-6 py-2 text-sm font-medium text-white hover:bg-indigo-700">
                  Checkout
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Products Grid */}
        <div className="mb-6">
          <h2 className="mb-4 text-2xl font-bold text-gray-900">
            {searchQuery ? `Search Results for "${searchQuery}"` : 'Featured Products'}
          </h2>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {filteredProducts.map((product) => (
              <div
                key={product.id}
                className="rounded-lg bg-white p-6 shadow hover:shadow-md transition-shadow"
              >
                <div className="mb-4 flex h-48 items-center justify-center rounded-lg bg-gray-100 text-6xl">
                  {product.image}
                </div>
                <h3 className="mb-2 text-lg font-semibold text-gray-900">
                  {product.name}
                </h3>
                <p className="mb-4 text-sm text-gray-600">
                  {product.description}
                </p>
                <div className="flex items-center justify-between">
                  <span className="text-xl font-bold text-gray-900">
                    ${product.price.toFixed(2)}
                  </span>
                  <button
                    onClick={() => addToCart(product)}
                    className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                  >
                    Add to Cart
                  </button>
                </div>
              </div>
            ))}
          </div>
          {filteredProducts.length === 0 && (
            <div className="rounded-lg bg-white p-8 text-center shadow">
              <p className="text-gray-600">No products found matching your search.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
